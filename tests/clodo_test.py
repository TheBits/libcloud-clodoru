import functools
import os
from collections import namedtuple
from pathlib import Path
from typing import Tuple

import pytest
import vcr
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState
from libcloud.dns.base import Record, Zone
from libcloud.dns.types import RecordType

from libcloudclodoru import ClodoConnection, ClodoDNSDriver, ClodoDriver


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


def filter_response(response):
    try:
        del response["headers"]["Set-Cookie"]
    except KeyError:
        pass

    if response["headers"].get("X-Auth-Token") is not None:
        response["headers"]["X-Auth-Token"] = ["[REDACTED]"]

    return response


def vcr_record(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        path = Path("./tests/fixtures/") / f"{f.__name__}.yaml"
        kwargs = dict(
            filter_headers=("X-Auth-Key", "X-Auth-User", "X-Auth-Token"),
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


@vcr_record
def test_compute_list_images(credentials):
    clodo = ClodoDriver(credentials.user_id, credentials.key)
    images = clodo.list_images()
    image = images[0]
    assert image.id == "1988"
    assert image.name == "Debian 9 32 bits"


@vcr_record
def test_dns_iterate_zones(credentials):
    clodo = ClodoDNSDriver(credentials.user_id, credentials.key)
    zones = clodo.iterate_zones()
    assert len(zones) == 2
    zone = zones[0]
    assert zone.id == "405290"
    assert zone.domain == "example1.ru"
    assert zone.type == "MASTER"


@vcr_record
def test_delete_zone(credentials):
    clodo = ClodoDNSDriver(credentials.user_id, credentials.key)
    zone = Zone(id="1", domain="test", type="test", ttl=1, driver=clodo)
    result = clodo.delete_zone(zone)
    assert result is True


@vcr_record
def test_create_zone(credentials):
    clodo = ClodoDNSDriver(credentials.user_id, credentials.key)
    domain = "example1.ru"
    zone_type = "MASTER"
    zone = clodo.create_zone(domain, zone_type)
    assert zone.id == "1"
    assert zone.domain == domain
    assert zone.type == zone_type


@vcr_record
def test_update_zone(credentials):
    clodo = ClodoDNSDriver(credentials.user_id, credentials.key)
    zone = Zone(id="1", domain="test", type="test", ttl=1, driver=clodo)
    response = clodo.update_zone(zone, "test2")
    assert response is True


@vcr_record
def test_delete_record(credentials):
    clodo = ClodoDNSDriver(credentials.user_id, credentials.key)
    zone = Zone(id="1", domain="test.ru", type="test", ttl=1, driver=clodo)
    record = Record(id="1", name="test", type=RecordType.AAAA, data="test", zone=zone, driver=clodo)
    result = clodo.delete_record(record)
    assert result is True


@vcr_record
def test_start_node(credentials):
    clodo = ClodoDriver(credentials.user_id, credentials.key)
    node = Node(id="1", name="test", state=NodeState.RUNNING, driver=clodo, private_ips=[], public_ips=[])
    result = clodo.start_node(node)
    assert result is True


@vcr_record
def test_stop_node(credentials):
    clodo = ClodoDriver(credentials.user_id, credentials.key)
    node = Node(id="1", name="test", state=NodeState.RUNNING, driver=clodo, private_ips=[], public_ips=[])
    result = clodo.start_node(node)
    assert result is True


@vcr_record
def test_reboot_node(credentials):
    clodo = ClodoDriver(credentials.user_id, credentials.key)
    node = Node(id="1", name="test", state=NodeState.RUNNING, driver=clodo, private_ips=[], public_ips=[])
    result = clodo.start_node(node)
    assert result is True


@vcr_record
def test_compute_list_nodes(credentials):
    clodo = ClodoDriver(credentials.user_id, credentials.key)
    nodes = clodo.list_nodes()
    assert len(nodes) == 2
    node1 = nodes[0]
    assert node1.id == "60"
    assert node1.image.id == "561"


@vcr_record
def test_destroy_node(credentials):
    clodo = ClodoDriver(credentials.user_id, credentials.key)
    node = Node(id="1", name="test", state=NodeState.RUNNING, driver=clodo, private_ips=[], public_ips=[])
    response = clodo.destroy_node(node)
    assert response is True
