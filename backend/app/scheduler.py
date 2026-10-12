import logging
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Playlist
from app.sync.engine import SyncAlreadyRunning, SyncResult
from app.yoto.errors import AuthRequired

log = logging.getLogger(__name__)

JOB_ID = "scheduled-sync"


async def run_scheduled_sync(
    sessions: sessionmaker[Session], sync: Callable[[int], Awaitable[SyncResult]]
) -> None:
    with sessions() as session:
        playlist_ids = session.scalars(
            select(Playlist.id).where(Playlist.auto_sync.is_(True)).order_by(Playlist.id)
        ).all()
    log.info("Scheduled sync of %d playlist(s)", len(playlist_ids))
    for playlist_id in playlist_ids:
        try:
            await sync(playlist_id)
        except SyncAlreadyRunning:
            continue
        except AuthRequired:
            log.warning("Yoto session expired; stopping the scheduled sync")
            return


def create_scheduler(cron: str, tz: str, job: Callable[[], Awaitable[None]]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        job,
        CronTrigger.from_crontab(cron, timezone=tz),
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    return scheduler
