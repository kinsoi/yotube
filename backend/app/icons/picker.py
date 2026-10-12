import logging
from dataclasses import dataclass
from typing import Protocol

from app.icons.catalog import IconCatalog
from app.icons.default_icon import PLAYLIST_COLORS, render_note_png
from app.icons.matcher import best_match, keywords, normalize
from app.yoto.models import Icon

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class IconChoice:
    media_id: str
    url: str


class KeywordSuggester(Protocol):
    async def suggest(self, title: str, artist: str) -> list[str]: ...


class IconUploader(Protocol):
    async def upload_icon(self, png: bytes, filename: str) -> Icon: ...


class SettingsStore(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...


class IconPicker:
    """Chooses a track icon: Claude keywords → title keywords → coloured music note."""

    def __init__(
        self,
        catalog: IconCatalog,
        uploader: IconUploader,
        settings: SettingsStore,
        suggester: KeywordSuggester | None = None,
    ) -> None:
        self._catalog = catalog
        self._uploader = uploader
        self._settings = settings
        self._suggester = suggester

    async def pick(self, title: str, artist: str, color: str) -> IconChoice | None:
        try:
            icons = await self._catalog.icons()
        except Exception:
            log.warning("Yoto icon catalog unavailable", exc_info=True)
            icons = []

        if icons and self._suggester is not None:
            try:
                words = [normalize(w) for w in await self._suggester.suggest(title, artist)]
                if match := best_match(words, icons):
                    return IconChoice(match.media_id, match.url)
            except Exception:
                log.warning("Claude icon suggestion failed for %r", title, exc_info=True)

        if icons and (match := best_match(keywords(title), icons)):
            return IconChoice(match.media_id, match.url)

        return await self.default_icon(color)

    async def default_icon(self, color: str) -> IconChoice | None:
        color = color if color in PLAYLIST_COLORS else "orange"
        key = f"default_icon:{color}"
        if stored := self._settings.get(key):
            media_id, url = stored.split("|", 1)
            return IconChoice(media_id, url)
        try:
            icon = await self._uploader.upload_icon(
                render_note_png(PLAYLIST_COLORS[color]), f"yotube-note-{color}.png"
            )
        except Exception:
            log.warning("Uploading the default icon failed", exc_info=True)
            return None
        self._settings.set(key, f"{icon.media_id}|{icon.url}")
        return IconChoice(icon.media_id, icon.url)
