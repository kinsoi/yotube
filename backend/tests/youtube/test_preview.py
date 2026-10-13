import httpx
import pytest
import respx

from app.youtube.models import AudioStream, DownloadFailed
from app.youtube.preview import AudioPreviewer

STREAM_URL = "https://rr1.googlevideo.com/videoplayback?id=1"
FRESH_URL = "https://rr2.googlevideo.com/videoplayback?id=2"


class FakeResolver:
    def __init__(self, *urls: str) -> None:
        self.urls = list(urls) or [STREAM_URL]
        self.calls: list[str] = []

    async def audio_stream(self, video_id: str) -> AudioStream:
        self.calls.append(video_id)
        url = self.urls[min(len(self.calls), len(self.urls)) - 1]
        return AudioStream(url, "audio/mp4", {"User-Agent": "yt-dlp-ua"})


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def read(preview) -> bytes:
    body = b"".join([chunk async for chunk in preview.body])
    await preview.close()
    return body


@respx.mock
async def test_forwards_the_range_and_returns_partial_content() -> None:
    route = respx.get(STREAM_URL).respond(
        206,
        content=b"abc",
        headers={
            "Content-Type": "audio/mp4",
            "Content-Range": "bytes 0-2/10",
            "Content-Length": "3",
            "Accept-Ranges": "bytes",
            "Set-Cookie": "secret=1",
        },
    )
    async with httpx.AsyncClient() as http:
        previewer = AudioPreviewer(FakeResolver(), http)
        preview = await previewer.open("v1", "bytes=0-2")
        assert await read(preview) == b"abc"

    request = route.calls.last.request
    assert request.headers["Range"] == "bytes=0-2"
    assert request.headers["User-Agent"] == "yt-dlp-ua"
    assert preview.status_code == 206
    assert preview.headers["content-range"] == "bytes 0-2/10"
    assert preview.headers["content-type"] == "audio/mp4"
    assert "set-cookie" not in preview.headers


@respx.mock
async def test_reuses_the_resolved_stream_while_it_is_fresh() -> None:
    respx.get(STREAM_URL).respond(200, content=b"abc")
    resolver = FakeResolver()
    clock = Clock()
    async with httpx.AsyncClient() as http:
        previewer = AudioPreviewer(resolver, http, ttl=60, clock=clock)
        await read(await previewer.open("v1", None))
        await read(await previewer.open("v1", "bytes=3-"))
        clock.now = 61
        await read(await previewer.open("v1", None))
    assert resolver.calls == ["v1", "v1"]


@respx.mock
async def test_resolves_again_when_youtube_refuses_a_cached_stream() -> None:
    respx.get(STREAM_URL).respond(403)
    respx.get(FRESH_URL).respond(200, content=b"fresh")
    resolver = FakeResolver(STREAM_URL, FRESH_URL)
    async with httpx.AsyncClient() as http:
        previewer = AudioPreviewer(resolver, http)
        assert await read(await previewer.open("v1", None)) == b"fresh"
        # The fresh stream replaced the refused one in the cache.
        assert await read(await previewer.open("v1", None)) == b"fresh"
    assert resolver.calls == ["v1", "v1"]


@respx.mock
async def test_raises_download_failed_when_youtube_keeps_refusing() -> None:
    respx.get(STREAM_URL).respond(403)
    async with httpx.AsyncClient() as http:
        previewer = AudioPreviewer(FakeResolver(), http)
        with pytest.raises(DownloadFailed):
            await previewer.open("v1", None)
