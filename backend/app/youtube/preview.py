"""Relay a song's audio to the browser so it can be heard before it is added.

YouTube stream links only work from the IP that resolved them, so the browser cannot
use them directly: the server resolves the link once and relays the byte ranges the
browser's audio element asks for.
"""

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.youtube.models import AudioStream, DownloadFailed

STREAM_TTL_SECONDS = 30 * 60  # YouTube links last hours; resolving takes seconds
MAX_CACHED_STREAMS = 64
RELAYED_STATUSES = frozenset({200, 206, 416})
RELAYED_HEADERS = ("content-length", "content-range", "accept-ranges")


class StreamResolver(Protocol):
    async def audio_stream(self, video_id: str) -> AudioStream: ...


@dataclass(frozen=True)
class AudioPreview:
    status_code: int
    headers: dict[str, str]
    body: AsyncIterator[bytes]
    close: Callable[[], Awaitable[None]]


class AudioPreviewer:
    def __init__(
        self,
        music: StreamResolver,
        http: httpx.AsyncClient,
        *,
        ttl: float = STREAM_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._music = music
        self._http = http
        self._ttl = ttl
        self._clock = clock
        self._streams: dict[str, tuple[float, AudioStream]] = {}

    async def open(self, video_id: str, byte_range: str | None) -> AudioPreview:
        """Start relaying `video_id`; the caller must await `close` once the body is sent."""
        status = None
        for fresh in (False, True):  # a cached link may have expired: resolve once more
            stream = await self._resolve(video_id, fresh=fresh)
            headers = dict(stream.headers)
            if byte_range:
                headers["Range"] = byte_range
            request = self._http.build_request("GET", stream.url, headers=headers)
            response = await self._http.send(request, stream=True)
            status = response.status_code
            if status in RELAYED_STATUSES:
                relayed = {k: response.headers[k] for k in RELAYED_HEADERS if k in response.headers}
                relayed["content-type"] = stream.mime
                relayed["cache-control"] = "no-store"
                return AudioPreview(status, relayed, response.aiter_raw(), response.aclose)
            await response.aclose()
            self._streams.pop(video_id, None)
        raise DownloadFailed(f"YouTube refused the audio stream of {video_id} (HTTP {status})")

    async def _resolve(self, video_id: str, *, fresh: bool) -> AudioStream:
        now = self._clock()
        cached = self._streams.get(video_id)
        if cached and not fresh and now - cached[0] < self._ttl:
            return cached[1]
        stream = await self._music.audio_stream(video_id)
        self._streams.pop(video_id, None)
        self._streams[video_id] = (now, stream)
        while len(self._streams) > MAX_CACHED_STREAMS:
            self._streams.pop(next(iter(self._streams)))
        return stream
