import logging

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from app.api.deps import ApiProblem, ServicesDep
from app.api.schemas import AuthStatus
from app.yoto.errors import LoginError

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/auth/status", response_model=AuthStatus)
def auth_status(services: ServicesDep) -> AuthStatus:
    return AuthStatus(
        configured=bool(services.settings.yoto_client_id),
        connected=services.auth.is_connected(),
    )


@router.get("/api/auth/login")
def login(services: ServicesDep) -> RedirectResponse:
    if not services.settings.yoto_client_id:
        raise ApiProblem(400, "not_configured", "YOTO_CLIENT_ID is not set")
    return RedirectResponse(services.auth.authorization_url(), status_code=307)


@router.get("/auth/callback")
async def callback(
    services: ServicesDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code or not state:
        log.warning("Yoto login cancelled or failed: %s", error)
        return RedirectResponse("/#/settings?auth=error", status_code=303)
    try:
        await services.auth.handle_callback(code, state)
    except LoginError:
        log.warning("Yoto login failed", exc_info=True)
        return RedirectResponse("/#/settings?auth=error", status_code=303)
    return RedirectResponse("/#/settings?auth=ok", status_code=303)


@router.post("/api/auth/logout", status_code=204)
def logout(services: ServicesDep) -> Response:
    services.auth.logout()
    return Response(status_code=204)
