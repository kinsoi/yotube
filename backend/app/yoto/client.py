import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.yoto.errors import AuthRequired, ContentNotFound, YotoError
from app.yoto.models import Icon, UploadedAudio
from app.youtube.urls import is_allowed_image_url

log = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class TokenProvider(Protocol):
    async def access_token(self) -> str: ...


class YotoClient:
    """Thin async client for the Yoto API endpoints Yotube needs."""

    def __init__(
        self,
        tokens: TokenProvider,
        http: httpx.AsyncClient,
        base_url: str = "https://api.yotoplay.com",
        *,
        poll_interval: float = 1.0,
        poll_attempts: int = 180,
        retry_delays: Sequence[float] = (1.0, 2.0, 4.0),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._tokens = tokens
        self._http = http
        self._base = base_url.rstrip("/")
        self._poll_interval = poll_interval
        self._poll_attempts = poll_attempts
        self._retry_delays = tuple(retry_delays)
        self._sleep = sleep

    async def upload_audio(self, path: Path, mime: str) -> UploadedAudio:
        data = self._json(
            await self._request("GET", "/media/transcode/audio/uploadUrl"),
            "Requesting an upload URL",
        )
        upload = data["upload"]
        upload_url: str | None = upload.get("uploadUrl")
        upload_id = str(upload["uploadId"])

        if upload_url:  # Yoto returns no URL when it already has this exact file.
            content = await asyncio.to_thread(path.read_bytes)
            response = await self._http.put(
                upload_url, content=content, headers={"Content-Type": mime}
            )
            if response.is_error:
                raise YotoError(f"Uploading audio failed (HTTP {response.status_code})")

        for _ in range(self._poll_attempts):
            data = self._json(
                await self._request(
                    "GET", f"/media/upload/{upload_id}/transcoded", params={"loudnorm": "false"}
                ),
                "Checking transcoding status",
            )
            transcode = data.get("transcode") or {}
            sha256 = transcode.get("transcodedSha256")
            if sha256:
                info = transcode.get("transcodedInfo") or {}
                return UploadedAudio(
                    sha256=str(sha256),
                    duration=round(float(info.get("duration") or 0)),
                    file_size=int(info.get("fileSize") or 0),
                    channels=str(info.get("channels") or "stereo"),
                    format=str(info.get("format") or "aac"),
                )
            await self._sleep(self._poll_interval)
        raise YotoError("Yoto did not finish transcoding in time")

    async def upload_cover_from_url(self, image_url: str) -> str:
        if not is_allowed_image_url(image_url):
            raise YotoError("Cover image URL is not on an allowed host")
        image = await self._http.get(image_url, follow_redirects=False)
        if image.is_error:
            raise YotoError(f"Downloading the cover image failed (HTTP {image.status_code})")
        response = await self._request(
            "POST",
            "/media/coverImage/user/me/upload",
            params={"autoconvert": "true", "coverType": "default"},
            content=image.content,
            headers={"Content-Type": image.headers.get("Content-Type", "image/jpeg")},
        )
        return str(self._json(response, "Uploading the cover")["coverImage"]["mediaUrl"])

    async def upload_icon(self, png: bytes, filename: str) -> Icon:
        response = await self._request(
            "POST",
            "/media/displayIcons/user/me/upload",
            params={"autoConvert": "true", "filename": filename},
            content=png,
            headers={"Content-Type": "image/png"},
        )
        icon = self._json(response, "Uploading an icon")["displayIcon"]
        return Icon(media_id=str(icon["mediaId"]), title=filename, url=str(icon.get("url", "")))

    async def list_public_icons(self) -> list[Icon]:
        response = await self._request("GET", "/media/displayIcons/user/yoto")
        return [
            Icon(
                media_id=str(item["mediaId"]),
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                tags=tuple(str(tag) for tag in item.get("publicTags") or ()),
            )
            for item in self._json(response, "Listing public icons").get("displayIcons", [])
        ]

    async def save_content(self, body: dict[str, Any], card_id: str | None) -> str:
        payload = {**body, "cardId": card_id} if card_id else body
        response = await self._request("POST", "/content", json=payload)
        if (
            response.is_error
            and card_id is not None
            and response.status_code in (400, 404)
            and not await self._content_exists(card_id)
        ):
            raise ContentNotFound(card_id)
        return str(self._json(response, "Saving the playlist")["card"]["cardId"])

    async def delete_content(self, card_id: str) -> None:
        response = await self._request("DELETE", f"/content/{card_id}")
        if response.status_code != 404:
            self._json(response, "Deleting the playlist")

    async def _content_exists(self, card_id: str) -> bool:
        response = await self._request("GET", f"/content/{card_id}")
        if response.status_code == 404:
            return False
        if response.is_success:
            card = response.json().get("card") or {}
            return not card.get("deleted", False)
        return True

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        extra_headers: dict[str, str] = kwargs.pop("headers", {})
        delays: tuple[float | None, ...] = (*self._retry_delays, None)
        for delay in delays:
            headers = {
                "Authorization": f"Bearer {await self._tokens.access_token()}",
                "Accept": "application/json",
                **extra_headers,
            }
            try:
                response = await self._http.request(
                    method, f"{self._base}{path}", headers=headers, **kwargs
                )
            except httpx.TransportError as exc:
                if delay is None:
                    raise YotoError(f"Network error while calling Yoto: {exc}") from exc
                log.warning("Yoto %s %s failed (%s), retrying", method, path, exc)
                await self._sleep(delay)
                continue
            if response.status_code == 401:
                raise AuthRequired("Yoto rejected the access token")
            if response.status_code in RETRYABLE_STATUS and delay is not None:
                log.warning("Yoto %s %s returned %s, retrying", method, path, response.status_code)
                await self._sleep(delay)
                continue
            return response
        raise AssertionError("unreachable")

    @staticmethod
    def _json(response: httpx.Response, action: str) -> dict[str, Any]:
        if response.is_error:
            raise YotoError(f"{action} failed (HTTP {response.status_code}): {response.text[:300]}")
        data: dict[str, Any] = response.json()
        return data
