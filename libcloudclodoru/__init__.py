from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import Node, NodeDriver, NodeImage
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
