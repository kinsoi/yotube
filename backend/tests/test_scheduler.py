from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.db.models import Playlist
from app.scheduler import create_scheduler, run_scheduled_sync
from app.sync.engine import SyncAlreadyRunning, SyncResult
from app.yoto.errors import AuthRequired


def add(session_factory, title: str, auto_sync: bool) -> int:
    with session_factory.begin() as session:
        playlist = Playlist(title=title, source_type="manual", auto_sync=auto_sync)
        session.add(playlist)
        session.flush()
        return playlist.id


async def test_syncs_only_auto_sync_playlists_in_order(session_factory) -> None:
    first = add(session_factory, "A", True)
    add(session_factory, "B", False)
    third = add(session_factory, "C", True)
    synced: list[int] = []

    async def sync(pid: int) -> SyncResult:
        synced.append(pid)
        return SyncResult("ok")

    await run_scheduled_sync(session_factory, sync)
    assert synced == [first, third]


async def test_stops_when_yoto_session_expired(session_factory) -> None:
    add(session_factory, "A", True)
    add(session_factory, "B", True)
    calls: list[int] = []

    async def sync(pid: int) -> SyncResult:
        calls.append(pid)
        raise AuthRequired("expired")

    await run_scheduled_sync(session_factory, sync)
    assert len(calls) == 1


async def test_skips_playlists_already_running(session_factory) -> None:
    add(session_factory, "A", True)
    second = add(session_factory, "B", True)
    synced: list[int] = []

    async def sync(pid: int) -> SyncResult:
        if pid != second:
            raise SyncAlreadyRunning(pid)
        synced.append(pid)
        return SyncResult("ok")

    await run_scheduled_sync(session_factory, sync)
    assert synced == [second]


async def test_scheduler_fires_at_cron_time_in_timezone() -> None:
    async def job() -> None:
        return None

    scheduler = create_scheduler("0 3 * * *", "Europe/Paris", job)
    trigger = scheduler.get_job("scheduled-sync").trigger
    paris = ZoneInfo("Europe/Paris")
    next_run = trigger.get_next_fire_time(None, datetime(2026, 10, 12, 12, 0, tzinfo=paris))
    assert next_run == datetime(2026, 10, 13, 3, 0, tzinfo=paris)


def test_invalid_cron_is_rejected() -> None:
    async def job() -> None:
        return None

    with pytest.raises(ValueError):
        create_scheduler("every night", "Europe/Paris", job)
