import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import httpx
from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Playlist, Track, UploadedMedia
from app.sync.mirror import UNAVAILABLE_MESSAGE, mirror_tracks
from app.sync.ports import IconChooser, MusicSource, YotoGateway
from app.sync.progress import ProgressCallback, SyncProgress
from app.timeutil import utcnow
from app.yoto.content import MAX_CHAPTERS, ContentTrack, build_content
from app.yoto.errors import AuthRequired, ContentNotFound, YotoError
from app.yoto.models import UploadedAudio
from app.youtube.models import DownloadFailed, PlaylistNotFound, TrackUnavailable, YouTubeError

log = logging.getLogger(__name__)

TRANSIENT_ERRORS = (DownloadFailed, YotoError, httpx.HTTPError, OSError)
INTERRUPTED_MESSAGE = "Interrupted (the app was restarted)"


class SyncAlreadyRunning(Exception):
    """A sync for this playlist is already in progress."""


class SyncError(Exception):
    """A sync could not complete; `code` lets the UI show a localized message."""

    def __init__(self, message: str, code: str = "unknown") -> None:
        super().__init__(message)
        self.code = code


def error_code(exc: Exception) -> str:
    """Stable, localizable identifier for a sync failure."""
    if isinstance(exc, SyncError):
        return exc.code
    if isinstance(exc, AuthRequired):
        return "auth_required"
    if isinstance(exc, PlaylistNotFound):
        return "source_empty"
    if isinstance(exc, YotoError):
        return "yoto_error"
    if isinstance(exc, YouTubeError):
        return "youtube_error"
    return "unknown"


@dataclass(frozen=True)
class SyncResult:
    status: Literal["ok", "partial", "error"]
    uploaded: int = 0
    failed: int = 0
    message: str | None = None


def _no_progress(_progress: SyncProgress) -> None:
    return None


Operation = Callable[[int, ProgressCallback], Awaitable[SyncResult]]


class SyncEngine:
    """Mirrors a playlist source into a Yoto playlist."""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        music: MusicSource,
        yoto: YotoGateway,
        icons: IconChooser,
        *,
        rng: random.Random | None = None,
        concurrency: int = 2,
        retry_delays: Sequence[float] = (2.0, 5.0, 15.0),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._sessions = sessions
        self._music = music
        self._yoto = yoto
        self._icons = icons
        self._rng = rng or random.Random()
        self._concurrency = concurrency
        self._retry_delays = tuple(retry_delays)
        self._sleep = sleep
        self._lock = asyncio.Lock()  # one sync at a time, app-wide
        self._running: set[int] = set()

    def is_running(self, playlist_id: int) -> bool:
        return playlist_id in self._running

    async def sync(self, playlist_id: int, progress: ProgressCallback = _no_progress) -> SyncResult:
        """Fetch the source, upload what is missing and rewrite the Yoto playlist."""
        return await self._run(playlist_id, progress, self._sync)

    async def rebuild(
        self, playlist_id: int, progress: ProgressCallback = _no_progress
    ) -> SyncResult:
        """Rewrite the Yoto playlist (title, order, shuffle, icons) without fetching/uploading."""
        return await self._run(playlist_id, progress, self._rebuild)

    async def _run(
        self, playlist_id: int, progress: ProgressCallback, operation: Operation
    ) -> SyncResult:
        if playlist_id in self._running:
            raise SyncAlreadyRunning(playlist_id)
        self._running.add(playlist_id)
        try:
            async with self._lock:
                self._set_status(playlist_id, "running", None, touch=False)
                try:
                    result = await operation(playlist_id, progress)
                except AuthRequired as exc:
                    self._set_status(playlist_id, "error", str(exc), code=error_code(exc))
                    progress(SyncProgress(playlist_id, "error", message=str(exc)))
                    raise
                except Exception as exc:
                    log.exception("Sync of playlist %s failed", playlist_id)
                    self._set_status(playlist_id, "error", str(exc), code=error_code(exc))
                    progress(SyncProgress(playlist_id, "error", message=str(exc)))
                    return SyncResult("error", message=str(exc))
                self._set_status(playlist_id, result.status, result.message)
                progress(SyncProgress(playlist_id, "done", message=result.message))
                return result
        finally:
            self._running.discard(playlist_id)

    async def _sync(self, playlist_id: int, progress: ProgressCallback) -> SyncResult:
        with self._sessions() as session:
            playlist = self._get(session, playlist_id)
            source_type, source_url = playlist.source_type, playlist.source_url

        if source_type == "youtube":
            progress(SyncProgress(playlist_id, "fetching"))
            info = await self._music.get_playlist(source_url or "")
            if not info.tracks:
                raise SyncError("The YouTube Music playlist is empty or private", "source_empty")
            with self._sessions.begin() as session:
                playlist = self._get(session, playlist_id)
                mirror_tracks(playlist, info.tracks)
                if not playlist.cover_url:
                    playlist.cover_url = info.thumbnail_url

        uploaded = await self._upload_missing(playlist_id, progress)
        await self._assign_icons(playlist_id, progress)
        await self._ensure_cover(playlist_id)
        sent = await self._save_content(playlist_id, progress)
        return self._outcome(playlist_id, sent, uploaded)

    async def _rebuild(self, playlist_id: int, progress: ProgressCallback) -> SyncResult:
        sent = await self._save_content(playlist_id, progress)
        return self._outcome(playlist_id, sent, uploaded=0)

    async def _upload_missing(self, playlist_id: int, progress: ProgressCallback) -> int:
        with self._sessions.begin() as session:
            tracks = session.scalars(
                select(Track).where(Track.playlist_id == playlist_id).order_by(Track.position)
            ).all()
            cached = set(
                session.scalars(
                    select(UploadedMedia.video_id).where(
                        UploadedMedia.video_id.in_({t.video_id for t in tracks})
                    )
                )
            )
            todo: dict[str, str] = {}  # video_id -> title, each video transferred once
            for track in tracks:
                # Only the source's own flag is skipped; a track marked unavailable by a
                # failed download is retried like a pending one.
                flagged = track.status == "unavailable" and track.error == UNAVAILABLE_MESSAGE
                if track.video_id in cached:
                    if not flagged:
                        track.status, track.error = "uploaded", None
                elif not flagged:
                    todo.setdefault(track.video_id, track.title)

        total = len(todo)
        done = 0
        uploaded = 0
        semaphore = asyncio.Semaphore(self._concurrency)

        async def transfer(video_id: str, title: str) -> None:
            nonlocal done, uploaded
            async with semaphore:
                progress(SyncProgress(playlist_id, "uploading", done, total, title))
                try:
                    media = await self._with_retries(lambda: self._transfer(video_id))
                except AuthRequired:
                    raise
                except TrackUnavailable as exc:
                    self._set_track_status(playlist_id, video_id, "unavailable", str(exc))
                except Exception as exc:
                    log.warning("Could not transfer %s: %s", video_id, exc)
                    self._set_track_status(playlist_id, video_id, "error", str(exc))
                else:
                    self._store_media(playlist_id, video_id, media)
                    uploaded += 1
                done += 1
                progress(SyncProgress(playlist_id, "uploading", done, total, title))

        try:
            async with asyncio.TaskGroup() as group:
                for video_id, title in todo.items():
                    group.create_task(transfer(video_id, title))
        except* AuthRequired as errors:
            raise errors.exceptions[0] from None
        return uploaded

    async def _transfer(self, video_id: str) -> UploadedAudio:
        audio = await self._music.download_audio(video_id)
        try:
            return await self._yoto.upload_audio(audio.path, audio.mime)
        finally:
            audio.path.unlink(missing_ok=True)

    async def _with_retries(
        self, operation: Callable[[], Awaitable[UploadedAudio]]
    ) -> UploadedAudio:
        delays: tuple[float | None, ...] = (*self._retry_delays, None)
        for delay in delays:
            try:
                return await operation()
            except (AuthRequired, TrackUnavailable):
                raise
            except TRANSIENT_ERRORS as exc:
                if delay is None:
                    raise
                log.warning("Transfer failed (%s), retrying in %ss", exc, delay)
                await self._sleep(delay)
        raise AssertionError("unreachable")

    async def _assign_icons(self, playlist_id: int, progress: ProgressCallback) -> None:
        with self._sessions() as session:
            playlist = self._get(session, playlist_id)
            color = playlist.color
            pending = [
                (t.id, t.title, t.artist)
                for t in playlist.tracks
                if t.icon_id is None and not t.icon_manual
            ]
        for index, (track_id, title, artist) in enumerate(pending, start=1):
            progress(SyncProgress(playlist_id, "icons", index, len(pending), title))
            choice = await self._icons.pick(title, artist, color)
            if choice is None:
                continue
            with self._sessions.begin() as session:
                track = session.get(Track, track_id)
                if track is not None and not track.icon_manual:
                    track.icon_id, track.icon_url = choice.media_id, choice.url

    async def _ensure_cover(self, playlist_id: int) -> None:
        with self._sessions() as session:
            playlist = self._get(session, playlist_id)
            cover_url, uploaded_cover = playlist.cover_url, playlist.yoto_cover_url
        if not cover_url or uploaded_cover:
            return
        try:
            yoto_cover = await self._yoto.upload_cover_from_url(cover_url)
        except AuthRequired:
            raise
        except Exception:
            log.warning("Cover upload failed for playlist %s", playlist_id, exc_info=True)
            return
        with self._sessions.begin() as session:
            self._get(session, playlist_id).yoto_cover_url = yoto_cover

    async def _save_content(self, playlist_id: int, progress: ProgressCallback) -> int:
        progress(SyncProgress(playlist_id, "saving"))
        with self._sessions() as session:
            playlist = self._get(session, playlist_id)
            rows = session.execute(
                select(Track, UploadedMedia)
                .join(UploadedMedia, UploadedMedia.video_id == Track.video_id)
                .where(Track.playlist_id == playlist_id)
                .order_by(Track.position)
            ).all()
            title, shuffle = playlist.title, playlist.shuffle
            card_id, cover = playlist.yoto_card_id, playlist.yoto_cover_url
            tracks = [
                ContentTrack(
                    t.title, m.sha256, m.duration, m.file_size, m.channels, m.format, t.icon_id
                )
                for t, m in rows
            ]
        if not tracks:
            raise SyncError("No track could be sent to Yoto", "nothing_sent")
        if shuffle:
            self._rng.shuffle(tracks)

        body = build_content(title, tracks, shuffle=shuffle, cover_url=cover)
        try:
            new_card_id = await self._yoto.save_content(body, card_id)
        except ContentNotFound:
            log.info("Yoto playlist %s no longer exists; creating a new one", card_id)
            new_card_id = await self._yoto.save_content(body, None)

        with self._sessions.begin() as session:
            self._get(session, playlist_id).yoto_card_id = new_card_id
        return len(tracks)

    def _outcome(self, playlist_id: int, sent: int, uploaded: int) -> SyncResult:
        with self._sessions() as session:
            missing = (
                session.scalar(
                    select(func.count())
                    .select_from(Track)
                    .outerjoin(UploadedMedia, UploadedMedia.video_id == Track.video_id)
                    .where(Track.playlist_id == playlist_id, UploadedMedia.video_id.is_(None))
                )
                or 0
            )
        status: Literal["ok", "partial"] = "partial" if missing or sent > MAX_CHAPTERS else "ok"
        return SyncResult(status, uploaded=uploaded, failed=missing)

    def _store_media(self, playlist_id: int, video_id: str, media: UploadedAudio) -> None:
        with self._sessions.begin() as session:
            session.merge(
                UploadedMedia(
                    video_id=video_id,
                    sha256=media.sha256,
                    duration=media.duration,
                    file_size=media.file_size,
                    channels=media.channels,
                    format=media.format,
                )
            )
            session.execute(
                update(Track)
                .where(Track.playlist_id == playlist_id, Track.video_id == video_id)
                .values(status="uploaded", error=None)
            )

    def _set_track_status(self, playlist_id: int, video_id: str, status: str, error: str) -> None:
        with self._sessions.begin() as session:
            session.execute(
                update(Track)
                .where(Track.playlist_id == playlist_id, Track.video_id == video_id)
                .values(status=status, error=error[:500])
            )

    def _set_status(
        self,
        playlist_id: int,
        status: str,
        error: str | None,
        *,
        code: str | None = None,
        touch: bool = True,
    ) -> None:
        with self._sessions.begin() as session:
            playlist = session.get(Playlist, playlist_id)
            if playlist is None:
                return
            playlist.last_sync_status = status
            playlist.last_sync_error = error[:1000] if error else None
            playlist.last_sync_error_code = code if error else None
            if touch:
                playlist.last_sync_at = utcnow()

    @staticmethod
    def _get(session: Session, playlist_id: int) -> Playlist:
        playlist = session.get(Playlist, playlist_id)
        if playlist is None:
            raise SyncError(f"Playlist {playlist_id} does not exist")
        return playlist


def reset_interrupted(sessions: sessionmaker[Session]) -> int:
    """Mark playlists left 'running' by a previous process as failed. Returns how many."""
    with sessions.begin() as session:
        result = session.execute(
            update(Playlist)
            .where(Playlist.last_sync_status == "running")
            .values(
                last_sync_status="error",
                last_sync_error=INTERRUPTED_MESSAGE,
                last_sync_error_code="interrupted",
            )
        )
        assert isinstance(result, CursorResult)
        return int(result.rowcount or 0)
