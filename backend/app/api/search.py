from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ServicesDep
from app.api.schemas import PlaylistPreview, TrackInfoOut

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
