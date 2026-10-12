from typing import cast, get_args

from fastapi import APIRouter

from app.api.deps import ServicesDep
from app.api.schemas import Language, SettingsOut, SettingsUpdate
from app.services import Services

router = APIRouter(prefix="/api")

LANGUAGE_KEY = "language"


def _settings(services: Services) -> SettingsOut:
    stored = services.settings_store.get(LANGUAGE_KEY)
    language = cast(Language, stored) if stored in get_args(Language) else None
    return SettingsOut(
        language=language,
        sync_cron=services.settings.sync_cron,
        timezone=services.settings.tz,
        icon_ai_enabled=services.icon_ai_enabled,
        yoto_configured=bool(services.settings.yoto_client_id),
        yoto_connected=services.auth.is_connected(),
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings(services: ServicesDep) -> SettingsOut:
    return _settings(services)


@router.patch("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, services: ServicesDep) -> SettingsOut:
    services.settings_store.set(LANGUAGE_KEY, body.language)
    return _settings(services)
