from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import is_allowed_host

PUBLIC = "http://yotube.example.com:8080"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    # No lifespan: the middleware answers before any route needs the services.
    app = create_app(Settings(data_dir=tmp_path, public_url=PUBLIC, allowed_hosts="nas"))
    return TestClient(app, base_url="http://localhost:8080")


@pytest.mark.parametrize(
    "host",
    [
        "yotube.example.com",  # host of PUBLIC_URL
        "localhost",
        "127.0.0.1",
        "::1",
        "192.168.1.20",
        "10.0.0.5",
        "fe80::1",
        "nas.local",
        "nas.lan",
        "box.home",
        "yotube.internal",
        "nas",  # ALLOWED_HOSTS
        "NAS.Local.",
    ],
)
def test_allowed_hosts(host: str) -> None:
    assert is_allowed_host(host, {"yotube.example.com", "nas"})


@pytest.mark.parametrize(
    "host", ["evil.com", "rebind.attacker.net", "local", "nas.local.evil.com", "", "nas2"]
)
def test_refused_hosts(host: str) -> None:
    assert not is_allowed_host(host, {"yotube.example.com", "nas"})


def test_star_disables_the_host_check() -> None:
    assert is_allowed_host("anything.example.org", {"*"})


@pytest.mark.parametrize(
    "header",
    [
        "localhost:8080",
        "yotube.example.com:8080",
        "[::1]:8080",
        "192.168.1.20",
        "nas.local:9000",
        "nas:8080",
    ],
)
def test_requests_with_an_allowed_host_header_pass(client, header) -> None:
    response = client.get("/api/health", headers={"host": header})
    assert response.status_code == 200


@pytest.mark.parametrize("header", ["evil.com", "evil.com:8080", "rebind.attacker.net:80"])
def test_requests_with_an_unknown_host_header_are_refused(client, header) -> None:
    response = client.get("/api/health", headers={"host": header})
    assert response.status_code == 400
    assert response.json()["code"] == "host_not_allowed"


def test_testserver_is_not_allowed_by_default(tmp_path) -> None:
    client = TestClient(create_app(Settings(data_dir=tmp_path)))
    assert client.get("/api/health").status_code == 400


def test_allowed_hosts_setting_reads_a_comma_separated_list(tmp_path) -> None:
    app = create_app(Settings(data_dir=tmp_path, allowed_hosts=" foo.example , bar.example"))
    for host in ("foo.example", "bar.example:8080"):
        response = TestClient(app).get("/api/health", headers={"host": host})
        assert response.status_code == 200


def test_allowed_hosts_star_accepts_any_host(tmp_path) -> None:
    app = create_app(Settings(data_dir=tmp_path, allowed_hosts="*"))
    assert TestClient(app).get("/api/health", headers={"host": "x.example"}).status_code == 200


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_cross_origin_writes_are_refused(client, method) -> None:
    response = client.request(method, "/api/health", headers={"origin": "https://evil.com"})
    assert response.status_code == 403
    assert response.json()["code"] == "cross_origin"


@pytest.mark.parametrize(
    "origin", ["http://localhost:9999", "null", "http://127.0.0.1:8080", "http://localhost"]
)
def test_origin_must_match_host_and_port(client, origin) -> None:
    response = client.post("/api/health", headers={"origin": origin})
    assert response.status_code == 403


def test_same_origin_and_originless_writes_pass(client) -> None:
    same = client.post("/api/health", headers={"origin": "http://localhost:8080"})
    assert same.status_code == 405  # reached the router
    assert client.post("/api/health").status_code == 405  # curl: no Origin


def test_default_ports_are_equivalent(client) -> None:
    response = client.post(
        "/api/health", headers={"host": "nas.local", "origin": "https://nas.local"}
    )
    assert response.status_code == 405


def test_cross_site_fetch_without_origin_is_refused(client) -> None:
    response = client.post("/api/health", headers={"sec-fetch-site": "cross-site"})
    assert (response.status_code, response.json()["code"]) == (403, "cross_origin")
    same = client.post("/api/health", headers={"sec-fetch-site": "same-origin"})
    assert same.status_code == 405


def test_safe_methods_ignore_the_origin(client) -> None:
    response = client.get("/api/health", headers={"origin": "https://evil.com"})
    assert response.status_code == 200


def test_cross_site_login_is_refused(client) -> None:
    response = client.get("/api/auth/login", headers={"sec-fetch-site": "cross-site"})
    assert (response.status_code, response.json()["code"]) == (403, "cross_origin")


def test_security_headers_on_every_response(client) -> None:
    for response in (
        client.get("/api/health"),
        client.get("/api/health", headers={"host": "evil.com"}),
        client.post("/api/health", headers={"origin": "https://evil.com"}),
        client.get("/nope"),
    ):
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "same-origin"
