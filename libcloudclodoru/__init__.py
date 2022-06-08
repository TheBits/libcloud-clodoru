from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import Node, NodeDriver, NodeImage
from libcloud.compute.types import NodeState
from libcloud.dns.base import DNSDriver, Zone
from libcloud.utils.py3 import httplib


class ClodoResponse(JsonResponse):
    def success(self):
        return super().success() or (self.status == httplib.NO_CONTENT)

    def parse_error(self):
        body = super().parse_error()

        # INFO: пример ответа: {"code":401,"message":"Unauthorized","details":"..."}
        code = body["code"]
        if code == 401:
            raise InvalidCredsError(value=body["details"])

        # TODO: ServiceUnavailableError и RateLimitReachedError

        return body


class ClodoConnection(ConnectionUserAndKey):
    responseCls = ClodoResponse
    host = "api.clodo.ru"
    token = None
    token_expired = None
    token_issued = None

    def add_default_headers(self, headers):
        headers["Accept"] = "application/json"
        headers["X-Auth-Token"] = self.token
        return headers

    def __init__(self, *args, **kwargs):
        if kwargs.get("url") is None:
            kwargs["url"] = "https://api.clodo.ru/"
        super().__init__(*args, **kwargs)

        headers = {
            "X-Auth-User": self.user_id,
            "X-Auth-Key": self.key,
        }

        response = self.request(
            action="/",
            method="GET",
            headers=headers,
        )

        self.token = response.headers["X-Auth-Token".lower()]

        # TODO: сделать datetime
        self.token_expired = response.headers["X-Auth-Token-Expired".lower()]
        self.token_issued = response.headers["X-Auth-Token-Issued".lower()]

        # TODO: удалять self.conntion что бы пересоздать кооннект на новый base_url
        self.base_url = response.headers["X-Server-Management-Url".lower()]


class ClodoDriver(NodeDriver):
    connectionCls = ClodoConnection
    name = "Clodo"
    website = "https://clodo.ru/"

    NODE_STATE_MAP = {
        "is_running": NodeState.RUNNING,
        "is_stopped": NodeState.STOPPED,
        "billing": NodeState.SUSPENDED,
        "queued": NodeState.PENDING,
    }

    # TODO: NODE_STATE_MAP https://github.com/TheBits/libcloud-clodoru/issues/22

    def list_images(self, location=None):
        images = []
        response = self.connection.request("v1/images")
        for image in response.object["images"]:
            image_id = image.pop("id")
            image_name = image.pop("name")
            images.append(NodeImage(image_id, image_name, self, extra=image))
        return images

    def _make_action(self, node_id: int, action: str) -> bool:
        response = self.connection.request(
            "v1/servers/{id}/action".format(id=node_id),
            data={action: ""},
            method="POST",
        )
        return response.status == httplib.NO_CONTENT

    def start_node(self, node: Node) -> bool:
        return self._make_action(node.id, "start")

    def reboot_node(self, node: Node) -> bool:
        return self._make_action(node.id, "reboot")

    def stop_node(self, node: Node) -> bool:
        return self._make_action(node.id, "stop")

    def list_nodes(self):
        response = self.connection.request("v1/servers")
        nodes = []
        for n in response.object.get("servers", {}).get("server", []):
            state = self.NODE_STATE_MAP.get(n["status"], NodeState.UNKNOWN)

            private_ips = []
            private_addresses = n.get("addresses", {}).get("private", {})
            if private_addresses:
                for addr in private_addresses.get("ip").items():
                    private_ips.append(addr.get("addr"))

            public_ips = []
            public_addresses = n.get("addresses", {}).get("public", {})
            if public_addresses:
                for addr in public_addresses.get("ip"):
                    private_ips.append(addr.get("addr"))

            image = NodeImage(n["imageId"], name=n["os_type"], driver=self)

            node = Node(
                id=n["id"],
                name=n["name"],
                state=state,
                public_ips=public_ips,
                private_ips=private_ips,
                driver=self,
                image=image,
                extra=n,
            )
            nodes.append(node)
        return nodes


    def destroy_node(self, node: Node) -> bool:
        response = self.connection.request("v1/servers/{id}".format(id=node.id), method="DELETE")
        return response.status == httplib.NO_CONTENT


class ClodoDNSDriver(DNSDriver):
    connectionCls = ClodoConnection
    name = "Clodo"
    website = "https://clodo.ru/"

    # TODO: RECORD_TYPE_MAP

    def iterate_zones(self):
        zones = []
        response = self.connection.request("v1/dns")
        for element in response.object["dns"]["domains"]:
            zone_id = element.pop("id")
            domain = element.pop("name")
            zone_type = element.pop("type")
            zone = Zone(
                id=zone_id,
                domain=domain,
                type=zone_type,
                ttl=None,
                driver=self,
                extra=element,
            )
            zones.append(zone)
        return zones

    def list_zones(self):
        return self.iterate_zones()
