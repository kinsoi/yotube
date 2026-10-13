import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import auth, events, icons, playlists, search
from app.api import settings as settings_api
from app.api.errors import register_error_handlers
from app.config import Settings, get_settings
from app.scheduler import create_scheduler
from app.security import SecurityMiddleware, allowed_hosts_from
from app.services import Services, build_services

log = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    services_factory: Callable[[Settings], Services] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if services_factory is not None:  # tests
            app.state.services = services_factory(settings)
            yield
            return
        async with AsyncExitStack() as stack:
            services = await build_services(settings, stack)
            app.state.services = services
            scheduler = create_scheduler(settings.sync_cron, settings.tz, services.scheduled_sync)
            scheduler.start()
            stack.callback(scheduler.shutdown, wait=False)
            if not settings.yoto_client_id:
                log.warning("YOTO_CLIENT_ID is not set: Yoto login is disabled")
            yield

    app = FastAPI(title="Yotube", lifespan=lifespan)
    app.state.settings = settings
    register_error_handlers(app)
    app.add_middleware(
        SecurityMiddleware,
        allowed_hosts=allowed_hosts_from(settings.public_url, settings.allowed_hosts),
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (
        auth.router,
        search.router,
        playlists.router,
        icons.router,
        settings_api.router,
        events.router,
    ):
        app.include_router(router)

    if settings.static_dir and settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
    return app
