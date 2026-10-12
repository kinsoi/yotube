from datetime import datetime, timedelta

import pytest

from app.icons.catalog import IconCatalog
from app.yoto.models import Icon

ICONS = [Icon("m1", "Lion", "u1", ("animal",)), Icon("m2", "Train", "u2", ("vehicle",))]


class FakeSource:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    async def list_public_icons(self) -> list[Icon]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("Yoto down")
        return ICONS


async def test_icons_are_cached_until_ttl_expires() -> None:
    now = [datetime(2026, 10, 12)]
    source = FakeSource()
    catalog = IconCatalog(source, ttl=timedelta(hours=1), clock=lambda: now[0])

    assert await catalog.icons() == ICONS
    assert await catalog.icons() == ICONS
    assert source.calls == 1

    now[0] += timedelta(hours=2)
    await catalog.icons()
    assert source.calls == 2


async def test_stale_icons_are_kept_when_refresh_fails() -> None:
    now = [datetime(2026, 10, 12)]
    source = FakeSource()
    catalog = IconCatalog(source, ttl=timedelta(hours=1), clock=lambda: now[0])
    await catalog.icons()
    source.fail = True
    now[0] += timedelta(hours=2)
    assert await catalog.icons() == ICONS


async def test_first_load_failure_propagates() -> None:
    source = FakeSource()
    source.fail = True
    with pytest.raises(RuntimeError):
        await IconCatalog(source).icons()


async def test_search_ranks_and_empty_query_lists_all() -> None:
    catalog = IconCatalog(FakeSource())
    assert await catalog.search("train") == [ICONS[1]]
    assert await catalog.search("  ") == ICONS
    assert await catalog.search("", limit=1) == ICONS[:1]
