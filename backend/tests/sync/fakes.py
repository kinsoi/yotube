import asyncio
from pathlib import Path
from typing import Any

from app.icons.picker import IconChoice
from app.yoto.errors import AuthRequired, ContentNotFound
from app.yoto.models import UploadedAudio
from app.youtube.models import (
    DownloadedAudio,
    DownloadFailed,
    PlaylistInfo,
    PlaylistNotFound,
    TrackInfo,
    TrackUnavailable,
)

SOURCE_URL = "https://music.youtube.com/playlist?list=PLkids00000"


def track_info(video_id: str, available: bool = True) -> TrackInfo:
    return TrackInfo(
        video_id, f"Song {video_id}", "Artist", 120, f"https://t/{video_id}.jpg", available
    )


def playlist_info(*video_ids: str, unavailable: tuple[str, ...] = ()) -> PlaylistInfo:
    tracks = [track_info(v, v not in unavailable) for v in video_ids]
    return PlaylistInfo("PLkids", "Kids", "https://t/pl.jpg", tracks)


class FakeMusic:
    def __init__(self, tmp_dir: Path) -> None:
        self.tmp_dir = tmp_dir
        self.playlists: dict[str, PlaylistInfo] = {}
        self.unavailable: set[str] = set()
        self.flaky: dict[str, int] = {}  # video_id -> number of failures before success
        self.downloads: list[str] = []
        self.files: list[Path] = []
        self.fetches = 0
        self.gate: asyncio.Event | None = None  # when set, get_playlist waits on it

    async def get_playlist(self, url_or_id: str) -> PlaylistInfo:
        self.fetches += 1
        if self.gate is not None:
            await self.gate.wait()
        if url_or_id not in self.playlists:
            raise PlaylistNotFound(f"Could not read playlist {url_or_id}")
        return self.playlists[url_or_id]

    async def download_audio(self, video_id: str) -> DownloadedAudio:
        self.downloads.append(video_id)
        if video_id in self.unavailable:
            raise TrackUnavailable(f"{video_id}: Video unavailable")
        if self.flaky.get(video_id, 0) > 0:
            self.flaky[video_id] -= 1
            raise DownloadFailed("timed out")
        path = self.tmp_dir / f"{video_id}.m4a"
        path.write_bytes(b"audio")
        self.files.append(path)
        return DownloadedAudio(path, "audio/mp4")


class FakeYoto:
    def __init__(self) -> None:
        self.uploads: list[str] = []
        self.saved: list[tuple[dict[str, Any], str]] = []
        self.covers: list[str] = []
        self.deleted: set[str] = set()
        self.auth_expired = False
        self._next_card = 0

    async def upload_audio(self, path: Path, mime: str) -> UploadedAudio:
        if self.auth_expired:
            raise AuthRequired("The Yoto session has expired")
        assert path.exists()  # noqa: ASYNC240
        self.uploads.append(path.stem)
        return UploadedAudio(f"sha-{path.stem}", 120, 1000, "stereo", "aac")

    async def upload_cover_from_url(self, image_url: str) -> str:
        self.covers.append(image_url)
        return f"https://cdn/cover{len(self.covers)}.jpg"

    async def save_content(self, body: dict[str, Any], card_id: str | None) -> str:
        if self.auth_expired:
            raise AuthRequired("The Yoto session has expired")
        if card_id is not None and card_id in self.deleted:
            raise ContentNotFound(card_id)
        if card_id is None:
            self._next_card += 1
            card_id = f"card-{self._next_card}"
        self.saved.append((body, card_id))
        return card_id

    def chapter_titles(self, index: int = -1) -> list[str]:
        return [chapter["title"] for chapter in self.saved[index][0]["content"]["chapters"]]


class FakeIcons:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def pick(self, title: str, artist: str, color: str) -> IconChoice | None:
        self.calls.append(title)
        return IconChoice(f"icon-{title}", f"https://i/{title}.png")
