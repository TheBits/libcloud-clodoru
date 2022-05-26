from libcloud.common.base import ConnectionUserAndKey, JsonResponse
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import NodeDriver
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

        user = kwargs.pop("user_id", None)
        key = kwargs.pop("key", None)

        headers = {
            "X-Auth-User": user,
            "X-Auth-Key": key,
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


class ClodoDriver(NodeDriver):
    connectionCls = ClodoConnection
    name = "Clodo"
    website = "https://clodo.ru/"
    # TODO: NODE_STATE_MAP
