from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrackInfo:
    video_id: str
    title: str
    artist: str
    duration: int | None
    thumbnail_url: str | None
    available: bool = True


@dataclass(frozen=True)
class PlaylistInfo:
    playlist_id: str
    title: str
    thumbnail_url: str | None
    tracks: list[TrackInfo]


@dataclass(frozen=True)
class DownloadedAudio:
    path: Path
    mime: str


class YouTubeError(Exception):
    """Base class for YouTube-side failures."""


class InvalidPlaylistUrl(YouTubeError):
    """The text is not a YouTube (Music) playlist link."""


class PlaylistNotFound(YouTubeError):
    """The playlist does not exist, is private, or could not be read."""


class TrackUnavailable(YouTubeError):
    """The video is permanently unavailable (removed, private, blocked…)."""


class DownloadFailed(YouTubeError):
    """A download failed for a reason that may be temporary."""
