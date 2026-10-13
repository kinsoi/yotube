import random
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.settings_store import DbSettingsStore
from app.events import EventBroker
from app.icons.catalog import IconCatalog
from app.main import create_app
from app.services import Services
from app.sync.engine import SyncAlreadyRunning, SyncEngine
from app.yoto.models import Icon
from app.youtube.models import AudioStream, TrackInfo
from app.youtube.preview import AudioPreviewer
from tests.sync.fakes import SOURCE_URL, FakeIcons, FakeMusic, FakeYoto, playlist_info


class FakeAuth:
    def __init__(self) -> None:
        self.connected = True
        self.callbacks: list[tuple[str, str]] = []

    def is_connected(self) -> bool:
        return self.connected

    def authorization_url(self) -> str:
        return "https://login.yotoplay.com/authorize?state=s1"

    async def handle_callback(self, code: str, state: str) -> None:
        self.callbacks.append((code, state))

    def logout(self) -> None:
        self.connected = False


PREVIEW_STREAM_URL = "https://rr1.googlevideo.com/videoplayback?id=preview"


class ApiMusic(FakeMusic):
    async def search(self, query: str, limit: int = 20) -> list[TrackInfo]:
        return [TrackInfo("v1", f"{query} song", "Anne", 100, None)]

    async def audio_stream(self, video_id: str) -> AudioStream:
        return AudioStream(PREVIEW_STREAM_URL, "audio/mp4", {})


class ApiYoto(FakeYoto):
    def __init__(self) -> None:
        super().__init__()
        self.deleted_cards: list[str] = []

    async def list_public_icons(self) -> list[Icon]:
        return [Icon("m-lion", "Lion", "https://i/lion.png", ("animal",))]

    async def delete_content(self, card_id: str) -> None:
        self.deleted_cards.append(card_id)


@dataclass
class RecordingServices(Services):
    started: list[tuple[int, bool]] = field(default_factory=list)
    running: set[int] = field(default_factory=set)

    def start_sync(self, playlist_id: int, *, rebuild: bool = False) -> None:
        if playlist_id in self.running:
            raise SyncAlreadyRunning(playlist_id)
        self.started.append((playlist_id, rebuild))


@pytest.fixture
async def preview_http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as http:
        yield http


@pytest.fixture
def services(session_factory, tmp_path, preview_http) -> RecordingServices:
    music = ApiMusic(tmp_path)
    music.playlists[SOURCE_URL] = playlist_info("a", "b")
    yoto = ApiYoto()
    return RecordingServices(
        settings=Settings(data_dir=tmp_path, yoto_client_id="client-1"),
        sessions=session_factory,
        auth=FakeAuth(),  # type: ignore[arg-type]
        yoto=yoto,  # type: ignore[arg-type]
        music=music,  # type: ignore[arg-type]
        catalog=IconCatalog(yoto),
        engine=SyncEngine(session_factory, music, yoto, FakeIcons(), rng=random.Random(1)),
        broker=EventBroker(),
        settings_store=DbSettingsStore(session_factory),
        icon_ai_enabled=False,
        previews=AudioPreviewer(music, preview_http),
    )


@pytest.fixture
def client(services, tmp_path) -> Iterator[TestClient]:
    app = create_app(Settings(data_dir=tmp_path), services_factory=lambda _: services)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def real_services(services) -> Services:
    """Services with the real start_sync (background task), unlike RecordingServices."""
    fields = {
        k: getattr(services, k)
        for k in Services.__dataclass_fields__
        if k not in {"_tasks", "_active", "_pending"}
    }
    return Services(**fields)


@pytest.fixture
def real_client(real_services, tmp_path) -> Iterator[TestClient]:
    app = create_app(Settings(data_dir=tmp_path), services_factory=lambda _: real_services)
    with TestClient(app) as test_client:
        yield test_client
