import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.icons.matcher import keywords, normalize, rank
from app.timeutil import utcnow
from app.yoto.models import Icon

log = logging.getLogger(__name__)


class IconSource(Protocol):
    async def list_public_icons(self) -> list[Icon]: ...


class KeywordSuggester(Protocol):
    async def suggest(self, title: str, artist: str) -> list[str]: ...


@dataclass(frozen=True)
class IconSearch:
    icons: list[Icon]
    matched: bool  # False: nothing fits the query, `icons` is the whole catalogue to browse


class IconCatalog:
    """Yoto's public icon list, cached in memory and refreshed once a day."""

    def __init__(
        self,
        source: IconSource,
        ttl: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = utcnow,
        suggester: KeywordSuggester | None = None,
    ) -> None:
        self._source = source
        self._suggester = suggester
        self._ttl = ttl
        self._clock = clock
        self._icons: list[Icon] = []
        self._loaded_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def icons(self) -> list[Icon]:
        async with self._lock:
            fresh = self._loaded_at is not None and self._clock() - self._loaded_at < self._ttl
            if not fresh:
                try:
                    # Yoto's list repeats some icons; the UI keys icons by media id.
                    unique: dict[str, Icon] = {}
                    for icon in await self._source.list_public_icons():
                        unique.setdefault(icon.media_id, icon)
                    self._icons = list(unique.values())
                    self._loaded_at = self._clock()
                except Exception:
                    if not self._icons:
                        raise
                    log.warning("Refreshing Yoto icons failed; keeping cached list", exc_info=True)
            return self._icons

    async def search(self, query: str, limit: int = 60) -> IconSearch:
        """Icons matching `query`; when none does, related words from Claude, else everything."""
        icons = await self.icons()
        if not query.strip():
            return IconSearch(icons[:limit], matched=True)
        words = keywords(query) or [normalize(query.strip())]
        if found := rank(words, icons) or await self._suggested(query, icons):
            return IconSearch(found[:limit], matched=True)
        return IconSearch(icons, matched=False)

    async def _suggested(self, query: str, icons: list[Icon]) -> list[Icon]:
        if self._suggester is None:
            return []
        try:
            words = [normalize(word) for word in await self._suggester.suggest(query, "")]
        except Exception:
            log.warning("Claude icon suggestion failed for %r", query, exc_info=True)
            return []
        return rank(words, icons)
