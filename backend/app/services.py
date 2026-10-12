import asyncio
import logging
import shutil
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

import httpx
from anthropic import AsyncAnthropic
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.migrate import run_migrations
from app.db.session import make_engine, make_session_factory
from app.db.settings_store import DbSettingsStore
from app.db.token_store import DbTokenStore
from app.events import EventBroker
from app.icons.catalog import IconCatalog
from app.icons.claude import ClaudeKeywordSuggester
from app.icons.picker import IconPicker
from app.scheduler import run_scheduled_sync
from app.sync.engine import SyncAlreadyRunning, SyncEngine, SyncResult, reset_interrupted
from app.sync.progress import SyncProgress
from app.yoto.auth import YotoAuth
from app.yoto.client import YotoClient
from app.yoto.errors import AuthRequired
from app.youtube.source import YouTubeMusicSource

log = logging.getLogger(__name__)


@dataclass
class Services:
    settings: Settings
    sessions: sessionmaker[Session]
    auth: YotoAuth
    yoto: YotoClient
    music: YouTubeMusicSource
    catalog: IconCatalog
    engine: SyncEngine
    broker: EventBroker
    settings_store: DbSettingsStore
    icon_ai_enabled: bool
    _tasks: set[asyncio.Task[None]] = field(default_factory=set)

    def start_sync(self, playlist_id: int, *, rebuild: bool = False) -> None:
        if self.engine.is_running(playlist_id):
            raise SyncAlreadyRunning(playlist_id)
        task = asyncio.create_task(self._sync(playlist_id, rebuild))
        self._tasks.add(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and (exc := task.exception()) is not None:
            log.error("Background sync failed", exc_info=exc)

    async def scheduled_sync(self) -> None:
        await run_scheduled_sync(self.sessions, self._sync_and_notify)

    async def _sync(self, playlist_id: int, rebuild: bool) -> None:
        try:
            if rebuild:
                await self.engine.rebuild(playlist_id, self._publish_progress)
            else:
                await self.engine.sync(playlist_id, self._publish_progress)
        except AuthRequired:
            self.broker.publish({"type": "auth_required"})
        except SyncAlreadyRunning:
            return
        self.broker.publish({"type": "playlist_updated", "playlist_id": playlist_id})

    async def _sync_and_notify(self, playlist_id: int) -> SyncResult:
        try:
            return await self.engine.sync(playlist_id, self._publish_progress)
        except AuthRequired:
            self.broker.publish({"type": "auth_required"})
            raise
        finally:
            self.broker.publish({"type": "playlist_updated", "playlist_id": playlist_id})

    def _publish_progress(self, progress: SyncProgress) -> None:
        self.broker.publish({"type": "progress", **progress.to_dict()})


async def build_services(settings: Settings, stack: AsyncExitStack) -> Services:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(settings.tmp_dir, ignore_errors=True)  # leftovers of an interrupted sync
    settings.tmp_dir.mkdir(parents=True)

    run_migrations(settings.database_url)
    db_engine = make_engine(settings.database_url)
    stack.callback(db_engine.dispose)
    sessions = make_session_factory(db_engine)
    if reset := reset_interrupted(sessions):
        log.info("Marked %d interrupted sync(s) as failed", reset)

    http = await stack.enter_async_context(
        httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0), follow_redirects=True)
    )
    auth = YotoAuth(
        settings.yoto_client_id,
        settings.yoto_auth_url,
        settings.redirect_uri,
        DbTokenStore(sessions),
        http,
    )
    yoto = YotoClient(auth, http, settings.yoto_api_url)
    music = YouTubeMusicSource(settings.tmp_dir)
    catalog = IconCatalog(yoto)
    settings_store = DbSettingsStore(sessions)

    suggester = None
    if settings.anthropic_api_key:
        anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        stack.push_async_callback(anthropic_client.close)
        suggester = ClaudeKeywordSuggester(anthropic_client, settings.anthropic_model)

    picker = IconPicker(catalog, yoto, settings_store, suggester)
    engine = SyncEngine(sessions, music, yoto, picker)
    return Services(
        settings=settings,
        sessions=sessions,
        auth=auth,
        yoto=yoto,
        music=music,
        catalog=catalog,
        engine=engine,
        broker=EventBroker(),
        settings_store=settings_store,
        icon_ai_enabled=suggester is not None,
    )
