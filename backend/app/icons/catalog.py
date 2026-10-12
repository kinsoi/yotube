import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol

from app.icons.matcher import keywords, normalize, rank
from app.timeutil import utcnow
from app.yoto.models import Icon

log = logging.getLogger(__name__)


class IconSource(Protocol):
    async def list_public_icons(self) -> list[Icon]: ...


class IconCatalog:
    """Yoto's public icon list, cached in memory and refreshed once a day."""

    def __init__(
        self,
        source: IconSource,
        ttl: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._source = source
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
                    self._icons = await self._source.list_public_icons()
                    self._loaded_at = self._clock()
                except Exception:
                    if not self._icons:
                        raise
                    log.warning("Refreshing Yoto icons failed; keeping cached list", exc_info=True)
            return self._icons

    async def search(self, query: str, limit: int = 60) -> list[Icon]:
        icons = await self.icons()
        if not query.strip():
            return icons[:limit]
        words = keywords(query) or [normalize(query.strip())]
        return rank(words, icons)[:limit]
