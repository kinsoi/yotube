from typing import Annotated

from fastapi import APIRouter, Path, Query, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.api.deps import ServicesDep
from app.api.schemas import PlaylistPreview, TrackInfoOut
from app.youtube.urls import VIDEO_ID_PATTERN

router = APIRouter(prefix="/api")


@router.get("/search", response_model=list[TrackInfoOut])
async def search(
    q: Annotated[str, Query(min_length=1, max_length=200)], services: ServicesDep
) -> list[TrackInfoOut]:
    return [TrackInfoOut.model_validate(t) for t in await services.music.search(q)]


@router.get("/youtube/playlist", response_model=PlaylistPreview)
async def preview_playlist(
    url: Annotated[str, Query(min_length=1, max_length=500)], services: ServicesDep
) -> PlaylistPreview:
    info = await services.music.get_playlist(url)
    return PlaylistPreview(
        playlist_id=info.playlist_id,
        title=info.title,
        thumbnail_url=info.thumbnail_url,
        tracks=[TrackInfoOut.model_validate(t) for t in info.tracks],
    )


@router.get("/preview/{video_id}", response_class=StreamingResponse)
async def preview_audio(
    video_id: Annotated[str, Path(pattern=VIDEO_ID_PATTERN)],
    request: Request,
    services: ServicesDep,
) -> StreamingResponse:
    """Relay a song's audio so the browser can play it before it is added."""
    preview = await services.previews.open(video_id, request.headers.get("range"))
    return StreamingResponse(
        preview.body,
        status_code=preview.status_code,
        headers=preview.headers,
        media_type=preview.headers["content-type"],
        background=BackgroundTask(preview.close),
    )
