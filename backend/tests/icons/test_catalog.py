from datetime import datetime, timedelta

import pytest

from app.icons.catalog import IconCatalog, IconSearch
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
    assert await catalog.search("train") == IconSearch([ICONS[1]], matched=True)
    assert await catalog.search("  ") == IconSearch(ICONS, matched=True)
    assert await catalog.search("", limit=1) == IconSearch(ICONS[:1], matched=True)


async def test_search_without_match_offers_the_whole_catalogue() -> None:
    catalog = IconCatalog(FakeSource())
    assert await catalog.search("georgian disco", limit=1) == IconSearch(ICONS, matched=False)


class FakeSuggester:
    def __init__(self, words: list[str], fail: bool = False) -> None:
        self.words = words
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    async def suggest(self, title: str, artist: str) -> list[str]:
        self.calls.append((title, artist))
        if self.fail:
            raise RuntimeError("Claude down")
        return self.words


async def test_search_without_match_asks_claude_for_related_words() -> None:
    suggester = FakeSuggester(["Train", "car"])
    catalog = IconCatalog(FakeSource(), suggester=suggester)
    assert await catalog.search("choo choo") == IconSearch([ICONS[1]], matched=True)
    assert suggester.calls == [("choo choo", "")]


async def test_search_with_a_match_does_not_ask_claude() -> None:
    suggester = FakeSuggester(["train"])
    catalog = IconCatalog(FakeSource(), suggester=suggester)
    await catalog.search("lion")
    assert suggester.calls == []


async def test_search_falls_back_to_the_catalogue_when_claude_fails() -> None:
    catalog = IconCatalog(FakeSource(), suggester=FakeSuggester([], fail=True))
    assert await catalog.search("choo choo") == IconSearch(ICONS, matched=False)


async def test_duplicate_icons_from_yoto_are_listed_once() -> None:
    class DuplicatingSource(FakeSource):
        async def list_public_icons(self) -> list[Icon]:
            return [*ICONS, Icon("m1", "Lion again", "u1b", ())]

    assert await IconCatalog(DuplicatingSource()).icons() == ICONS


async def test_claude_suggestions_are_cached_per_query() -> None:
    suggester = FakeSuggester(["train"])
    catalog = IconCatalog(FakeSource(), suggester=suggester)
    first = await catalog.search("choo choo")
    again = await catalog.search("  Choo Choo ")
    assert first == again
    assert len(suggester.calls) == 1


async def test_claude_suggestion_cache_is_bounded() -> None:
    suggester = FakeSuggester(["train"])
    catalog = IconCatalog(FakeSource(), suggester=suggester)
    for n in range(130):
        await catalog.search(f"zzz{n}")
    await catalog.search("zzz129")  # recent: cached
    assert len(suggester.calls) == 130
    await catalog.search("zzz0")  # evicted
    assert len(suggester.calls) == 131


async def test_failed_claude_suggestions_are_not_cached() -> None:
    suggester = FakeSuggester([], fail=True)
    catalog = IconCatalog(FakeSource(), suggester=suggester)
    await catalog.search("choo choo")
    await catalog.search("choo choo")
    assert len(suggester.calls) == 2
