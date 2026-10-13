import asyncio
from typing import Any

import pytest

from app.events import EventBroker
from app.services import Services
from app.sync.engine import SyncAlreadyRunning, SyncError, SyncResult


class GatedEngine:
    """Engine fake: the first run blocks until `gate` is set; one run per playlist at a time."""

    def __init__(self) -> None:
        self.running: set[int] = set()
        self.calls: list[tuple[int, str]] = []
        self.gate = asyncio.Event()
        self.missing: set[int] = set()

    def is_running(self, playlist_id: int) -> bool:
        return playlist_id in self.running

    async def _run(self, playlist_id: int, kind: str) -> SyncResult:
        if playlist_id in self.missing:
            raise SyncError(f"Playlist {playlist_id} does not exist")
        if playlist_id in self.running:
            raise SyncAlreadyRunning(playlist_id)
        self.running.add(playlist_id)
        self.calls.append((playlist_id, kind))
        try:
            if len(self.calls) == 1:
                await self.gate.wait()
            return SyncResult("ok")
        finally:
            self.running.discard(playlist_id)

    async def sync(self, playlist_id: int, progress: Any = None) -> SyncResult:
        return await self._run(playlist_id, "sync")

    async def rebuild(self, playlist_id: int, progress: Any = None) -> SyncResult:
        return await self._run(playlist_id, "rebuild")


def make_services(engine: GatedEngine) -> Services:
    return Services(
        settings=None,  # type: ignore[arg-type]
        sessions=None,  # type: ignore[arg-type]
        auth=None,  # type: ignore[arg-type]
        yoto=None,  # type: ignore[arg-type]
        music=None,  # type: ignore[arg-type]
        catalog=None,  # type: ignore[arg-type]
        engine=engine,  # type: ignore[arg-type]
        broker=EventBroker(),
        settings_store=None,  # type: ignore[arg-type]
        icon_ai_enabled=False,
        previews=None,  # type: ignore[arg-type]
    )


async def drain(services: Services) -> None:
    for _ in range(20):
        await asyncio.sleep(0)
        if services._tasks:
            await asyncio.gather(*list(services._tasks), return_exceptions=True)


async def test_queued_request_survives_a_scheduled_run_on_the_same_playlist() -> None:
    engine = GatedEngine()
    services = make_services(engine)
    services.start_sync(1)  # manual sync in flight
    await asyncio.sleep(0)
    services.request_sync(1, rebuild=True)  # user edit queued
    assert services._pending == {1: True}

    with pytest.raises(SyncAlreadyRunning):
        await services._sync_and_notify(1)  # the nightly run reaches playlist 1
    assert services._pending == {1: True}

    engine.gate.set()
    await drain(services)
    assert engine.calls == [(1, "sync"), (1, "rebuild")]
    assert services._pending == {}


async def test_run_pending_puts_the_request_back_when_a_sync_is_running() -> None:
    engine = GatedEngine()
    services = make_services(engine)
    services._pending[1] = False
    services._active.add(1)  # another task owns the playlist
    services._run_pending(1)
    assert services._pending == {1: False}
