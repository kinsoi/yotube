from pathlib import Path
from typing import Any

import pytest
from yt_dlp.utils import DownloadError

from app.youtube.models import (
    AudioStream,
    DownloadedAudio,
    DownloadFailed,
    PlaylistInfo,
    PlaylistNotFound,
    TrackInfo,
    TrackUnavailable,
)
from app.youtube.source import YouTubeMusicSource

PL = "PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"
VID = "lionSong-01"


def raw_track(video_id: str | None, title: str, **extra: Any) -> dict[str, Any]:
    return {
        "videoId": video_id,
        "title": title,
        "artists": [{"name": "Anne"}, {"name": "Bob"}],
        "duration_seconds": 125,
        "thumbnails": [
            {"url": "https://t/small.jpg", "width": 60},
            {"url": "https://t/big.jpg", "width": 544},
        ],
        **extra,
    }


class FakeYTMusic:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, Any]] = []

    def search(self, query: str, filter: str, limit: int) -> list[dict[str, Any]]:
        self.calls.append(("search", query, filter))
        return [raw_track("v1", "Lion Song"), {"resultType": "video", "videoId": None}]

    def get_playlist(self, playlist_id: str, limit: int | None) -> dict[str, Any]:
        self.calls.append(("get_playlist", playlist_id, limit))
        if playlist_id != PL:
            raise Exception("Server returned HTTP 404")
        return {
            "title": "Kids mix",
            "thumbnails": [{"url": "https://t/pl.jpg", "width": 400}],
            "tracks": [
                raw_track("v1", "Lion Song"),
                raw_track("v2", "Gone Song", isAvailable=False),
                raw_track(None, "Local upload"),
            ],
        }


class FakeYdl:
    error: str | None = None
    ext = "m4a"
    empty_info = False

    def __init__(self, opts: dict[str, Any]) -> None:
        self.opts = opts

    def __enter__(self) -> "FakeYdl":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def extract_info(self, url: str, download: bool) -> dict[str, Any]:
        if FakeYdl.error:
            raise DownloadError(FakeYdl.error)
        if FakeYdl.empty_info:
            return {}
        if not download:
            return {
                "url": "https://rr1.googlevideo.com/videoplayback?id=1",
                "ext": FakeYdl.ext,
                "http_headers": {"User-Agent": "yt-dlp-ua"},
            }
        path = Path(self.opts["outtmpl"].replace("%(ext)s", FakeYdl.ext))
        path.write_bytes(b"audio")
        return {"requested_downloads": [{"filepath": str(path)}]}


@pytest.fixture
def source(tmp_path: Path) -> YouTubeMusicSource:
    FakeYdl.error = None
    FakeYdl.ext = "m4a"
    FakeYdl.empty_info = False
    return YouTubeMusicSource(tmp_path / "tmp", ytmusic=FakeYTMusic(), ydl_factory=FakeYdl)


async def test_search_maps_songs_and_skips_results_without_video(source) -> None:
    assert await source.search("lion") == [
        TrackInfo("v1", "Lion Song", "Anne, Bob", 125, "https://t/big.jpg")
    ]


async def test_get_playlist_resolves_link_and_maps_tracks(source) -> None:
    info = await source.get_playlist(f"https://music.youtube.com/playlist?list={PL}&si=x")
    assert info == PlaylistInfo(
        playlist_id=PL,
        title="Kids mix",
        thumbnail_url="https://t/pl.jpg",
        tracks=[
            TrackInfo("v1", "Lion Song", "Anne, Bob", 125, "https://t/big.jpg", True),
            TrackInfo("v2", "Gone Song", "Anne, Bob", 125, "https://t/big.jpg", False),
        ],
    )


async def test_unreadable_playlist_raises_not_found(source) -> None:
    with pytest.raises(PlaylistNotFound):
        await source.get_playlist("PLprivateplaylist0000000000")


async def test_download_returns_file_and_mime(source, tmp_path) -> None:
    audio = await source.download_audio(VID)
    assert audio == DownloadedAudio(tmp_path / "tmp" / f"{VID}.m4a", "audio/mp4")
    assert audio.path.read_bytes() == b"audio"


async def test_download_of_removed_video_raises_track_unavailable(source) -> None:
    FakeYdl.error = "ERROR: [youtube] v1: Video unavailable. This video has been removed"
    with pytest.raises(TrackUnavailable):
        await source.download_audio(VID)


async def test_other_download_errors_are_transient(source) -> None:
    FakeYdl.error = "ERROR: Unable to download webpage: <urlopen error timed out>"
    with pytest.raises(DownloadFailed):
        await source.download_audio(VID)


@pytest.mark.parametrize(
    "message",
    [
        "ERROR: [youtube] v1: Requested format is not available. Use --list-formats",
        "ERROR: [youtube] v1: This video is not available",
        "ERROR: [youtube] v1: Sign in to confirm you\u2019re not a bot",
        "ERROR: [youtube] v1: your IP is likely being blocked by YouTube",
    ],
)
async def test_transient_yt_dlp_messages_are_not_treated_as_unavailable(source, message) -> None:
    FakeYdl.error = message
    with pytest.raises(DownloadFailed):
        await source.download_audio(VID)


async def test_missing_downloaded_file_info_raises_download_failed(source) -> None:
    FakeYdl.empty_info = True
    with pytest.raises(DownloadFailed):
        await source.download_audio(VID)


async def test_audio_stream_resolves_a_playable_url_without_downloading(source, tmp_path) -> None:
    stream = await source.audio_stream(VID)
    assert stream == AudioStream(
        "https://rr1.googlevideo.com/videoplayback?id=1", "audio/mp4", {"User-Agent": "yt-dlp-ua"}
    )
    assert not (tmp_path / "tmp").exists() or not any((tmp_path / "tmp").iterdir())


async def test_audio_stream_of_removed_video_raises_track_unavailable(source) -> None:
    FakeYdl.error = "ERROR: [youtube] v1: Video unavailable. This video has been removed"
    with pytest.raises(TrackUnavailable):
        await source.audio_stream(VID)


async def test_audio_stream_without_url_raises_download_failed(source) -> None:
    FakeYdl.empty_info = True
    with pytest.raises(DownloadFailed):
        await source.audio_stream(VID)


class ExplodingYdl:
    def __init__(self, opts: dict[str, Any]) -> None:
        raise AssertionError("yt-dlp must not be called for an invalid video id")


@pytest.mark.parametrize("video_id", ["dQw4w9WgXcQ/../../x", "v1", "dQw4w9WgXcQ&x", ""])
async def test_invalid_video_ids_are_refused_before_yt_dlp(tmp_path, video_id) -> None:
    source = YouTubeMusicSource(tmp_path / "tmp", ytmusic=FakeYTMusic(), ydl_factory=ExplodingYdl)
    with pytest.raises(TrackUnavailable, match="Invalid video id"):
        await source.download_audio(video_id)
    with pytest.raises(TrackUnavailable, match="Invalid video id"):
        await source.audio_stream(video_id)
