import asyncio
import base64
import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from app.timeutil import utcnow
from app.yoto.errors import AuthRequired, LoginError

REFRESH_MARGIN = timedelta(seconds=60)
LOGIN_TTL = timedelta(minutes=15)
MAX_PENDING_LOGINS = 10


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: datetime


class TokenStore(Protocol):
    def load(self) -> TokenSet | None: ...
    def save(self, tokens: TokenSet) -> None: ...
    def clear(self) -> None: ...


def make_pkce_pair() -> tuple[str, str]:
    """Return a (code_verifier, S256 code_challenge) pair."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class YotoAuth:
    """OAuth 2 Authorization Code + PKCE against Yoto, with transparent token refresh."""

    SCOPES = "user:content:manage offline_access"
    AUDIENCE = "https://api.yotoplay.com"

    def __init__(
        self,
        client_id: str,
        auth_base_url: str,
        redirect_uri: str,
        store: TokenStore,
        http: httpx.AsyncClient,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._client_id = client_id
        self._base = auth_base_url.rstrip("/")
        self._redirect_uri = redirect_uri
        self._store = store
        self._http = http
        self._clock = clock
        self._pending: dict[str, tuple[str, datetime]] = {}  # state -> (code_verifier, started)
        self._lock = asyncio.Lock()

    def authorization_url(self) -> str:
        verifier, challenge = make_pkce_pair()
        state = secrets.token_urlsafe(16)
        self._prune_pending()
        self._pending[state] = (verifier, self._clock())
        while len(self._pending) > MAX_PENDING_LOGINS:
            self._pending.pop(next(iter(self._pending)))
        params = {
            "audience": self.AUDIENCE,
            "scope": self.SCOPES,
            "response_type": "code",
            "client_id": self._client_id,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "redirect_uri": self._redirect_uri,
            "state": state,
        }
        return f"{self._base}/authorize?{urlencode(params)}"

    def _prune_pending(self) -> None:
        oldest = self._clock() - LOGIN_TTL
        for state in [s for s, (_, started) in self._pending.items() if started < oldest]:
            del self._pending[state]

    async def handle_callback(self, code: str, state: str) -> None:
        self._prune_pending()
        pending = self._pending.pop(state, None)
        if pending is None:
            raise LoginError("Unknown or expired login attempt, please try again")
        try:
            response = await self._http.post(
                f"{self._base}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._client_id,
                    "code_verifier": pending[0],
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                },
            )
        except httpx.HTTPError as exc:
            raise LoginError(f"Could not reach Yoto ({type(exc).__name__})") from exc
        if response.is_error:
            raise LoginError(f"Yoto refused the login (HTTP {response.status_code})")
        try:
            self._store_tokens(response.json(), previous_refresh_token=None)
        except (KeyError, TypeError, ValueError) as exc:
            raise LoginError("Yoto returned an unexpected token response") from exc

    def is_connected(self) -> bool:
        return self._store.load() is not None

    def logout(self) -> None:
        self._store.clear()

    async def access_token(self) -> str:
        async with self._lock:
            tokens = self._store.load()
            if tokens is None:
                raise AuthRequired("Not connected to Yoto")
            if tokens.expires_at - REFRESH_MARGIN > self._clock():
                return tokens.access_token
            response = await self._http.post(
                f"{self._base}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id,
                    "refresh_token": tokens.refresh_token,
                },
            )
            if response.status_code in (400, 401, 403):
                self._store.clear()
                raise AuthRequired("The Yoto session has expired")
            response.raise_for_status()
            return self._store_tokens(response.json(), tokens.refresh_token).access_token

    def _store_tokens(
        self, payload: dict[str, Any], previous_refresh_token: str | None
    ) -> TokenSet:
        refresh_token = payload.get("refresh_token") or previous_refresh_token
        if not refresh_token:
            raise LoginError("Yoto did not return a refresh token (is offline_access enabled?)")
        tokens = TokenSet(
            access_token=str(payload["access_token"]),
            refresh_token=str(refresh_token),
            expires_at=self._clock() + timedelta(seconds=int(payload.get("expires_in", 3600))),
        )
        self._store.save(tokens)
        return tokens
