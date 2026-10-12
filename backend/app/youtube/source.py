import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp
from ytmusicapi import YTMusic

from app.youtube.models import (
    DownloadedAudio,
    DownloadFailed,
    PlaylistInfo,
    PlaylistNotFound,
    TrackInfo,
    TrackUnavailable,
)
from app.youtube.urls import parse_playlist_id

MIME_BY_EXTENSION = {
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "webm": "audio/webm",
    "opus": "audio/ogg",
    "ogg": "audio/ogg",
    "mp3": "audio/mpeg",
}

# yt-dlp error fragments that mean "this video will never download".
_UNAVAILABLE_MARKERS = (
    "video unavailable",
    "private video",
    "has been removed",
    "has been terminated",
    "copyright",
    "confirm your age",
    "who has blocked it",
)


class YouTubeMusicSource:
    """Reads YouTube Music (search, playlists) and downloads audio with yt-dlp."""

    def __init__(
        self,
        tmp_dir: Path,
        ytmusic: Any | None = None,
        ydl_factory: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self._tmp_dir = tmp_dir
        self._ytmusic = ytmusic
        self._ydl_factory = ydl_factory or yt_dlp.YoutubeDL

    def _client(self) -> Any:
        if self._ytmusic is None:
            self._ytmusic = YTMusic()
        return self._ytmusic

    async def search(self, query: str, limit: int = 20) -> list[TrackInfo]:
        results = await asyncio.to_thread(self._client().search, query, filter="songs", limit=limit)
        tracks = [track for raw in results if (track := _track_from(raw))]
        return tracks[:limit]

    async def get_playlist(self, url_or_id: str) -> PlaylistInfo:
        playlist_id = parse_playlist_id(url_or_id)
        try:
            raw = await asyncio.to_thread(self._client().get_playlist, playlist_id, limit=None)
        except Exception as exc:  # ytmusicapi raises bare Exceptions for HTTP errors
            raise PlaylistNotFound(f"Could not read playlist {playlist_id}: {exc}") from exc
        tracks = [track for item in raw.get("tracks") or [] if (track := _track_from(item))]
        return PlaylistInfo(
            playlist_id=playlist_id,
            title=raw.get("title") or playlist_id,
            thumbnail_url=_best_thumbnail(raw.get("thumbnails")),
            tracks=tracks,
        )

    async def download_audio(self, video_id: str) -> DownloadedAudio:
        return await asyncio.to_thread(self._download, video_id)

    def _download(self, video_id: str) -> DownloadedAudio:
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        options = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": str(self._tmp_dir / f"{video_id}.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
        }
        try:
            with self._ydl_factory(options) as ydl:
                info = ydl.extract_info(
                    f"https://music.youtube.com/watch?v={video_id}", download=True
                )
        except yt_dlp.utils.DownloadError as exc:
            message = str(exc)
            if any(marker in message.lower() for marker in _UNAVAILABLE_MARKERS):
                raise TrackUnavailable(message) from exc
            raise DownloadFailed(message) from exc
        try:
            path = Path(info["requested_downloads"][0]["filepath"])
        except (KeyError, IndexError, TypeError) as exc:
            raise DownloadFailed(f"yt-dlp returned no downloaded file for {video_id}") from exc
        mime = MIME_BY_EXTENSION.get(path.suffix.lstrip(".").lower(), "application/octet-stream")
        return DownloadedAudio(path=path, mime=mime)


def _track_from(raw: dict[str, Any]) -> TrackInfo | None:
    video_id = raw.get("videoId")
    if not video_id:
        return None
    artists = ", ".join(a["name"] for a in raw.get("artists") or [] if a.get("name"))
    return TrackInfo(
        video_id=str(video_id),
        title=raw.get("title") or str(video_id),
        artist=artists,
        duration=raw.get("duration_seconds"),
        thumbnail_url=_best_thumbnail(raw.get("thumbnails")),
        available=raw.get("isAvailable", True) is not False,
    )


def _best_thumbnail(thumbnails: list[dict[str, Any]] | None) -> str | None:
    if not thumbnails:
        return None
    return max(thumbnails, key=lambda t: t.get("width", 0)).get("url")
