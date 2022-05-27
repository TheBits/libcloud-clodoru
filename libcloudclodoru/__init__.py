from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import NodeDriver, NodeImage
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

    # TODO: NODE_STATE_MAP

    def list_images(self, location=None):
        images = []
        response = self.connection.request("v1/images")
        for image in response.object["images"]:
            image_id = image.pop("id")
            image_name = image.pop("name")
            images.append(NodeImage(image_id, image_name, self, extra=image))
        return images
