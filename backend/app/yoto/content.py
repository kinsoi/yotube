from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

MAX_CHAPTERS = 100


@dataclass(frozen=True)
class ContentTrack:
    title: str
    sha256: str
    duration: int
    file_size: int
    channels: str
    format: str
    icon_media_id: str | None = None


def build_content(
    title: str,
    tracks: Sequence[ContentTrack],
    *,
    shuffle: bool,
    cover_url: str | None = None,
) -> dict[str, Any]:
    """Build the JSON body of `POST /content`: one chapter per track, in the given order."""
    selected = list(tracks)[:MAX_CHAPTERS]
    content: dict[str, Any] = {
        "chapters": [_chapter(index, t) for index, t in enumerate(selected, start=1)],
        "playbackType": "linear",
    }
    if shuffle and len(selected) > 1:
        # Native player shuffle: reshuffles every time the card is played.
        last = len(selected) - 1
        content["config"] = {"shuffle": [{"start": 0, "end": last, "limit": len(selected)}]}

    total_size = sum(t.file_size for t in selected)
    metadata: dict[str, Any] = {
        "media": {
            "duration": sum(t.duration for t in selected),
            "fileSize": total_size,
            "readableFileSize": round(total_size / 1024 / 1024, 1),
        }
    }
    if cover_url:
        metadata["cover"] = {"imageL": cover_url}
    return {"title": title, "content": content, "metadata": metadata}


def _chapter(index: int, track: ContentTrack) -> dict[str, Any]:
    label = str(index)
    audio: dict[str, Any] = {
        "key": "01",
        "title": track.title,
        "trackUrl": f"yoto:#{track.sha256}",
        "duration": track.duration,
        "fileSize": track.file_size,
        "channels": int(track.channels) if track.channels.isdigit() else track.channels,
        "format": track.format,
        "type": "audio",
        "overlayLabel": label,
    }
    chapter: dict[str, Any] = {
        "key": f"{index:02d}",
        "title": track.title,
        "overlayLabel": label,
        "tracks": [audio],
    }
    if track.icon_media_id:
        display = {"icon16x16": f"yoto:#{track.icon_media_id}"}
        chapter["display"] = display
        audio["display"] = display
    return chapter
