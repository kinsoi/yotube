from pathlib import Path
from typing import Any, Protocol

from app.icons.picker import IconChoice
from app.yoto.models import UploadedAudio
from app.youtube.models import DownloadedAudio, PlaylistInfo


class MusicSource(Protocol):
    async def get_playlist(self, url_or_id: str) -> PlaylistInfo: ...
    async def download_audio(self, video_id: str) -> DownloadedAudio: ...


class YotoGateway(Protocol):
    async def upload_audio(self, path: Path, mime: str) -> UploadedAudio: ...
    async def upload_cover_from_url(self, image_url: str) -> str: ...
    async def save_content(self, body: dict[str, Any], card_id: str | None) -> str: ...


class IconChooser(Protocol):
    async def pick(self, title: str, artist: str, color: str) -> IconChoice | None: ...
