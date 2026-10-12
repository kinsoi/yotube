import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.api.deps import ServicesDep

router = APIRouter(prefix="/api")


@router.get("/events")
async def events(services: ServicesDep) -> EventSourceResponse:
    async def stream() -> AsyncIterator[dict[str, str]]:
        async with services.broker.subscribe() as queue:
            while True:
                event = await queue.get()
                yield {"data": json.dumps(event)}

    return EventSourceResponse(stream(), ping=15)
