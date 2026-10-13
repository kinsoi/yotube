from typing import Annotated

from fastapi import APIRouter, Body, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ApiProblem, ServicesDep
from app.api.schemas import (
    Accepted,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistSummary,
    PlaylistUpdate,
    TrackIconUpdate,
    TrackIn,
    TrackOut,
)
from app.db.models import Playlist, Track
from app.services import Services
from app.sync.engine import SyncAlreadyRunning
from app.sync.mirror import mirror_tracks
from app.youtube.models import TrackInfo
from app.youtube.urls import is_allowed_image_url, parse_playlist_id

router = APIRouter(prefix="/api/playlists")


def _get(session: Session, playlist_id: int) -> Playlist:
    playlist = session.get(Playlist, playlist_id)
    if playlist is None:
        raise ApiProblem(404, "not_found", "Playlist not found")
    return playlist


def _summary(playlist: Playlist, services: Services) -> PlaylistSummary:
    return PlaylistSummary(
        id=playlist.id,
        title=playlist.title,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        yoto_card_id=playlist.yoto_card_id,
        shuffle=playlist.shuffle,
        auto_sync=playlist.auto_sync,
        color=playlist.color,
        cover_url=playlist.cover_url,
        last_sync_at=playlist.last_sync_at,
        last_sync_status=playlist.last_sync_status,
        last_sync_error=playlist.last_sync_error,
        last_sync_error_code=playlist.last_sync_error_code,
        track_count=len(playlist.tracks),
        syncing=services.engine.is_running(playlist.id),
        icon_urls=[t.icon_url for t in playlist.tracks if t.icon_url][:4],
    )


def _detail(playlist: Playlist, services: Services) -> PlaylistDetail:
    return PlaylistDetail(
        **_summary(playlist, services).model_dump(),
        tracks=[TrackOut.model_validate(t) for t in playlist.tracks],
    )


def _infos(tracks: list[TrackIn]) -> list[TrackInfo]:
    return [TrackInfo(t.video_id, t.title, t.artist, t.duration, t.thumbnail_url) for t in tracks]


def _start(services: Services, playlist_id: int, *, rebuild: bool = False) -> None:
    # during a running sync the request is queued and runs right after it
    services.request_sync(playlist_id, rebuild=rebuild)


@router.get("", response_model=list[PlaylistSummary])
def list_playlists(services: ServicesDep) -> list[PlaylistSummary]:
    with services.sessions() as session:
        playlists = session.scalars(select(Playlist).order_by(Playlist.created_at.desc())).all()
        return [_summary(p, services) for p in playlists]


@router.post("", response_model=PlaylistDetail, status_code=201)
async def create_playlist(body: PlaylistCreate, services: ServicesDep) -> PlaylistDetail:
    source_url = None
    if body.source_type == "youtube":
        playlist_id = parse_playlist_id(body.source_url or "")
        source_url = f"https://music.youtube.com/playlist?list={playlist_id}"
    with services.sessions.begin() as session:
        playlist = Playlist(
            title=body.title,
            source_type=body.source_type,
            source_url=source_url,
            shuffle=body.shuffle,
            auto_sync=body.auto_sync and body.source_type == "youtube",
            color=body.color,
        )
        if body.source_type == "manual":
            mirror_tracks(playlist, _infos(body.tracks))
            playlist.cover_url = next(
                (t.thumbnail_url for t in body.tracks if is_allowed_image_url(t.thumbnail_url)),
                None,
            )
        session.add(playlist)
        session.flush()
        detail = _detail(playlist, services)
    _start(services, detail.id)
    return detail


@router.get("/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(playlist_id: int, services: ServicesDep) -> PlaylistDetail:
    with services.sessions() as session:
        return _detail(_get(session, playlist_id), services)


@router.patch("/{playlist_id}", response_model=PlaylistDetail)
async def update_playlist(
    playlist_id: int, body: PlaylistUpdate, services: ServicesDep
) -> PlaylistDetail:
    with services.sessions.begin() as session:
        playlist = _get(session, playlist_id)
        changes = body.model_dump(exclude_unset=True, exclude_none=True)
        needs_rebuild = playlist.yoto_card_id is not None and any(
            changes.get(name, getattr(playlist, name)) != getattr(playlist, name)
            for name in ("title", "shuffle")
        )
        for name, value in changes.items():
            setattr(playlist, name, value)
        detail = _detail(playlist, services)
    if needs_rebuild:
        _start(services, playlist_id, rebuild=True)
    return detail


@router.delete("/{playlist_id}", status_code=204)
async def delete_playlist(
    playlist_id: int, services: ServicesDep, delete_on_yoto: bool = False
) -> Response:
    if services.engine.is_running(playlist_id):
        raise SyncAlreadyRunning(playlist_id)
    with services.sessions() as session:
        card_id = _get(session, playlist_id).yoto_card_id
    if delete_on_yoto and card_id:
        await services.yoto.delete_content(card_id)
    with services.sessions.begin() as session:
        session.delete(_get(session, playlist_id))
    services.forget_queued(playlist_id)
    return Response(status_code=204)


@router.put("/{playlist_id}/tracks", response_model=PlaylistDetail)
async def replace_tracks(
    playlist_id: int,
    tracks: Annotated[list[TrackIn], Body(min_length=1, max_length=500)],
    services: ServicesDep,
) -> PlaylistDetail:
    with services.sessions.begin() as session:
        playlist = _get(session, playlist_id)
        if playlist.source_type != "manual":
            raise ApiProblem(
                409, "not_manual", "Tracks of an imported playlist come from YouTube Music"
            )
        mirror_tracks(playlist, _infos(tracks))
        session.flush()
        detail = _detail(playlist, services)
    _start(services, playlist_id)
    return detail


@router.patch("/{playlist_id}/tracks/{track_id}", response_model=TrackOut)
async def set_track_icon(
    playlist_id: int,
    track_id: int,
    body: TrackIconUpdate,
    services: ServicesDep,
) -> TrackOut:
    with services.sessions.begin() as session:
        track = session.get(Track, track_id)
        if track is None or track.playlist_id != playlist_id:
            raise ApiProblem(404, "not_found", "Track not found")
        track.icon_id, track.icon_url, track.icon_manual = body.icon_id, body.icon_url, True
        has_card = track.playlist.yoto_card_id is not None
        result = TrackOut.model_validate(track)
    if has_card:
        _start(services, playlist_id, rebuild=True)
    return result


@router.post("/{playlist_id}/sync", response_model=Accepted, status_code=202)
async def sync_playlist(playlist_id: int, services: ServicesDep) -> Accepted:
    with services.sessions() as session:
        _get(session, playlist_id)
    services.start_sync(playlist_id)  # SyncAlreadyRunning -> 409
    return Accepted()


@router.post("/{playlist_id}/reshuffle", response_model=Accepted, status_code=202)
async def reshuffle_playlist(playlist_id: int, services: ServicesDep) -> Accepted:
    with services.sessions() as session:
        if _get(session, playlist_id).yoto_card_id is None:
            raise ApiProblem(409, "not_synced", "Sync the playlist once before reshuffling")
    services.start_sync(playlist_id, rebuild=True)
    return Accepted()
