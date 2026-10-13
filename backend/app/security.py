"""Host / Origin checks and security headers.

Yotube has no login: anything that can reach it may use it. These checks stop a web page
opened by someone on the LAN from driving the API anyway, through DNS rebinding (an
unknown Host name) or cross-site requests (a foreign Origin), and forbid framing.
"""

import ipaddress
from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
LOCAL_SUFFIXES = (".local", ".lan", ".home", ".internal")
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443}
SECURITY_HEADERS = (
    (b"x-frame-options", b"DENY"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"same-origin"),
)


def _normalize(host: str) -> str:
    return host.strip().lower().rstrip(".")


def split_host_port(value: str) -> tuple[str, int | None]:
    """Split a Host header (`name`, `name:port`, `[v6]:port`) into a host and a port."""
    value = value.strip()
    if value.startswith("["):
        host, _, rest = value[1:].partition("]")
        port = rest[1:] if rest.startswith(":") else ""
    elif value.count(":") == 1:
        host, port = value.split(":")
    else:  # a bare name, or an unbracketed IPv6 literal
        host, port = value, ""
    return _normalize(host), int(port) if port.isdigit() else None


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def is_allowed_host(host: str, extra: Iterable[str]) -> bool:
    """True for local names, IP literals (rebinding needs a name) and configured names."""
    allowed = {_normalize(name) for name in extra}
    if "*" in allowed:
        return True
    host = _normalize(host)
    if not host:
        return False
    return host in LOCAL_HOSTS or host in allowed or host.endswith(LOCAL_SUFFIXES) or _is_ip(host)


def _same_origin(origin: str, host_header: str) -> bool:
    try:
        parsed = urlsplit(origin)
        origin_host, origin_port = _normalize(parsed.hostname or ""), parsed.port
    except ValueError:
        return False
    if not origin_host or parsed.scheme not in DEFAULT_PORTS:
        return False
    origin_port = origin_port or DEFAULT_PORTS[parsed.scheme]
    host, port = split_host_port(host_header)
    if host != origin_host:
        return False
    # Behind a TLS proxy the Host header carries no port while the Origin implies 443.
    return port == origin_port or (port is None and origin_port in (80, 443))


class SecurityMiddleware:
    """Refuses unknown Host names and cross-site writes; adds security headers."""

    def __init__(self, app: ASGIApp, *, allowed_hosts: Iterable[str]) -> None:
        self.app = app
        self.allowed_hosts = frozenset(allowed_hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS:
                    headers.setdefault(name.decode(), value.decode())
            await send(message)

        problem = self._check(scope)
        if problem is None:
            await self.app(scope, receive, send_with_headers)
            return
        status_code, code, detail = problem
        response = JSONResponse({"detail": detail, "code": code}, status_code=status_code)
        await response(scope, receive, send_with_headers)

    def _check(self, scope: Scope) -> tuple[int, str, str] | None:
        headers = Headers(scope=scope)
        host_header = headers.get("host", "")
        host, _ = split_host_port(host_header)
        if not is_allowed_host(host, self.allowed_hosts):
            return 400, "host_not_allowed", "This host name is not allowed; see ALLOWED_HOSTS"

        method = scope["method"]
        cross_site = headers.get("sec-fetch-site") == "cross-site"
        if method in UNSAFE_METHODS:
            origin = headers.get("origin")
            if origin is not None and not _same_origin(origin, host_header):
                return 403, "cross_origin", "Cross-origin requests are not allowed"
            if origin is None and cross_site:
                return 403, "cross_origin", "Cross-site requests are not allowed"
        elif scope["path"] == "/api/auth/login" and cross_site:
            return 403, "cross_origin", "Cross-site requests are not allowed"
        return None


def allowed_hosts_from(public_url: str, setting: str) -> set[str]:
    """The PUBLIC_URL host plus the comma-separated ALLOWED_HOSTS names."""
    hosts = {name.strip() for name in setting.split(",") if name.strip()}
    try:
        public_host = urlsplit(public_url).hostname
    except ValueError:
        public_host = None
    if public_host:
        hosts.add(public_host)
    return hosts
