import asyncio
import base64
import hashlib
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from app.yoto.auth import TokenSet, YotoAuth, make_pkce_pair
from app.yoto.errors import AuthRequired, LoginError

AUTH_BASE = "https://login.yotoplay.com"
TOKEN_URL = f"{AUTH_BASE}/oauth/token"
NOW = datetime(2026, 10, 12, 12, 0, 0)


class MemoryStore:
    def __init__(self, tokens: TokenSet | None = None) -> None:
        self.tokens = tokens

    def load(self) -> TokenSet | None:
        return self.tokens

    def save(self, tokens: TokenSet) -> None:
        self.tokens = tokens

    def clear(self) -> None:
        self.tokens = None


@pytest.fixture
async def http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


def make_auth(http: httpx.AsyncClient, store: MemoryStore) -> YotoAuth:
    return YotoAuth(
        client_id="client-1",
        auth_base_url=AUTH_BASE,
        redirect_uri="http://localhost:8080/auth/callback",
        store=store,
        http=http,
        clock=lambda: NOW,
    )


def form(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


def test_pkce_challenge_is_s256_of_verifier() -> None:
    verifier, challenge = make_pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    assert challenge == expected.rstrip(b"=").decode()
    assert 43 <= len(verifier) <= 128


async def test_authorization_url_has_pkce_scopes_and_audience(http) -> None:
    url = urlparse(make_auth(http, MemoryStore()).authorization_url())
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == f"{AUTH_BASE}/authorize"
    assert query["client_id"] == "client-1"
    assert query["response_type"] == "code"
    assert query["code_challenge_method"] == "S256"
    assert query["audience"] == "https://api.yotoplay.com"
    assert query["scope"] == "user:content:manage offline_access"
    assert query["redirect_uri"] == "http://localhost:8080/auth/callback"
    assert query["state"]


@respx.mock
async def test_callback_exchanges_code_and_stores_tokens(http) -> None:
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600}
        )
    )
    store = MemoryStore()
    auth = make_auth(http, store)
    state = parse_qs(urlparse(auth.authorization_url()).query)["state"][0]

    await auth.handle_callback("code-123", state)

    sent = form(route.calls.last.request)
    assert sent["grant_type"] == "authorization_code"
    assert sent["code"] == "code-123"
    assert sent["code_verifier"]
    assert sent["client_id"] == "client-1"
    assert store.tokens == TokenSet("a1", "r1", NOW + timedelta(seconds=3600))
    assert auth.is_connected()


async def test_callback_rejects_unknown_state(http) -> None:
    with pytest.raises(LoginError):
        await make_auth(http, MemoryStore()).handle_callback("code", "forged-state")


@respx.mock
async def test_callback_reports_token_endpoint_failure(http) -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(403, json={"error": "denied"}))
    auth = make_auth(http, MemoryStore())
    state = parse_qs(urlparse(auth.authorization_url()).query)["state"][0]
    with pytest.raises(LoginError):
        await auth.handle_callback("code", state)


async def test_access_token_returned_while_valid(http) -> None:
    store = MemoryStore(TokenSet("a1", "r1", NOW + timedelta(minutes=10)))
    assert await make_auth(http, store).access_token() == "a1"


@respx.mock
async def test_expired_token_is_refreshed_and_refresh_token_rotated(http) -> None:
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "a2", "refresh_token": "r2", "expires_in": 3600}
        )
    )
    store = MemoryStore(TokenSet("a1", "r1", NOW - timedelta(seconds=1)))

    assert await make_auth(http, store).access_token() == "a2"

    sent = form(route.calls.last.request)
    assert sent == {"grant_type": "refresh_token", "client_id": "client-1", "refresh_token": "r1"}
    assert store.tokens is not None and store.tokens.refresh_token == "r2"


@respx.mock
async def test_refresh_keeps_previous_refresh_token_when_none_returned(http) -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "a2", "expires_in": 3600})
    )
    store = MemoryStore(TokenSet("a1", "r1", NOW))
    await make_auth(http, store).access_token()
    assert store.tokens is not None and store.tokens.refresh_token == "r1"


@respx.mock
async def test_concurrent_callers_trigger_a_single_refresh(http) -> None:
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "a2", "refresh_token": "r2", "expires_in": 3600}
        )
    )
    auth = make_auth(http, MemoryStore(TokenSet("a1", "r1", NOW)))
    tokens = await asyncio.gather(*(auth.access_token() for _ in range(3)))
    assert tokens == ["a2", "a2", "a2"]
    assert route.call_count == 1


@respx.mock
async def test_rejected_refresh_clears_session(http) -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(403, json={"error": "invalid_grant"}))
    store = MemoryStore(TokenSet("a1", "r1", NOW))
    with pytest.raises(AuthRequired):
        await make_auth(http, store).access_token()
    assert store.tokens is None


async def test_access_token_without_login_raises(http) -> None:
    with pytest.raises(AuthRequired):
        await make_auth(http, MemoryStore()).access_token()


def test_logout_clears_tokens() -> None:
    store = MemoryStore(TokenSet("a1", "r1", NOW))
    auth = make_auth(httpx.AsyncClient(), store)
    auth.logout()
    assert store.tokens is None and not auth.is_connected()
