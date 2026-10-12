from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.deps import ApiProblem
from app.sync.engine import SyncAlreadyRunning
from app.yoto.errors import AuthRequired, YotoError
from app.youtube.models import InvalidPlaylistUrl, PlaylistNotFound, YouTubeError


def _problem(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiProblem)
    async def api_problem(_: Request, exc: ApiProblem) -> JSONResponse:
        return _problem(exc.status_code, exc.code, exc.detail)

    @app.exception_handler(InvalidPlaylistUrl)
    async def invalid_url(_: Request, exc: InvalidPlaylistUrl) -> JSONResponse:
        return _problem(400, "invalid_playlist_url", str(exc))

    @app.exception_handler(PlaylistNotFound)
    async def playlist_not_found(_: Request, exc: PlaylistNotFound) -> JSONResponse:
        return _problem(404, "playlist_not_found", str(exc))

    @app.exception_handler(YouTubeError)
    async def youtube_error(_: Request, exc: YouTubeError) -> JSONResponse:
        return _problem(502, "youtube_error", str(exc))

    @app.exception_handler(AuthRequired)
    async def auth_required(_: Request, exc: AuthRequired) -> JSONResponse:
        return _problem(401, "auth_required", str(exc))

    @app.exception_handler(YotoError)
    async def yoto_error(_: Request, exc: YotoError) -> JSONResponse:
        return _problem(502, "yoto_error", str(exc))

    @app.exception_handler(SyncAlreadyRunning)
    async def sync_running(_: Request, exc: SyncAlreadyRunning) -> JSONResponse:
        return _problem(409, "sync_running", "This playlist is already syncing")

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        return _problem(422, "validation_error", str(first.get("msg", "Invalid request")))
