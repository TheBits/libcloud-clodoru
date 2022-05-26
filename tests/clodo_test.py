import functools
import os
from collections import namedtuple
from pathlib import Path
from typing import Tuple

import pytest
import vcr
from libcloud.common.types import InvalidCredsError

from libcloudclodoru import ClodoConnection


@pytest.fixture()
def credentials() -> Tuple[str, str]:
    Creds = namedtuple("Creds", ("user_id", "key"))

    user_id = os.getenv("DRIVER_USER_ID")
    if user_id is None:
        pytest.exit("set up DRIVER_USER_ID environment variable")

    key = os.getenv("DRIVER_KEY")
    if key is None:
        pytest.exit("set up DRIVER_KEY environment variable")

    creds = Creds(user_id, key)

    return creds


cred_keys = ("username", "password", "key")


def filter_response(response):
    try:
        del response["headers"]["Set-Cookie"]
    except KeyError:
        pass

    response["headers"]["X-Auth-Token"] = ["[REDACTED]"]

    return response


def vcr_record(f):
    # > X-Auth-User: [REDACTED]
    # > X-Auth-Key: [REDACTED]
    filter_query = (
        ("username", "USERNAME"),
        ("password", "PASSWORD"),
        ("key", "KEY"),
        ("sessionToken", "SESSION_TOKEN"),
    )

    # < X-Server-Management-Url: https://api.clodo.ru/v1
    # < X-Auth-Token: [REDACTED]
    # < X-Auth-Token-Expired: 2022-05-02T16:38:15+0300
    # < X-Auth-Token-Issued: 2022-05-02T16:18:15+0300

    @functools.wraps(f)
    def wrapper(*args, **kwds):
        path = Path("./tests/fixtures/") / f"{f.__name__}.yaml"
        kwargs = dict(
            filter_post_data_parameters=cred_keys,
            filter_query_parameters=filter_query,
            filter_headers=("X-Auth-Key", "X-Auth-User"),
            match_on=["method", "path"],
            path=str(path),
        )
        if not path.exists():
            kwargs["before_record_response"] = filter_response
        with vcr.use_cassette(**kwargs):
            return f(*args, **kwds)

    return wrapper


@vcr_record
def test_logon_ok(credentials):
    clodo = ClodoConnection(**credentials._asdict())
    assert len(clodo.token)
    assert len(clodo.token_issued)
    assert len(clodo.token_expired)


@vcr_record
def test_logon_invalid_creds():
    with pytest.raises(InvalidCredsError):
        ClodoConnection(key="123", user_id="abc")
