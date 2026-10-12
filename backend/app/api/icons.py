from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ServicesDep
from app.api.schemas import IconOut

router = APIRouter(prefix="/api")


@router.get("/icons", response_model=list[IconOut])
async def search_icons(
    services: ServicesDep, q: Annotated[str, Query(max_length=100)] = ""
) -> list[IconOut]:
    icons = await services.catalog.search(q)
    return [IconOut(media_id=i.media_id, title=i.title, url=i.url) for i in icons]
