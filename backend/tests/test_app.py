from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_endpoint(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(data_dir=tmp_path, allowed_hosts="testserver")))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_derive_paths_and_redirect_uri(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, public_url="http://nas.local:8080/")
    assert settings.redirect_uri == "http://nas.local:8080/auth/callback"
    assert settings.database_url == f"sqlite:///{tmp_path / 'yotube.db'}"
    assert settings.tmp_dir == tmp_path / "tmp"


def test_settings_read_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("YOTO_CLIENT_ID", "abc123")
    monkeypatch.setenv("SYNC_CRON", "30 2 * * *")
    settings = Settings(data_dir=tmp_path)
    assert settings.yoto_client_id == "abc123"
    assert settings.sync_cron == "30 2 * * *"
    assert settings.anthropic_model == "claude-haiku-5-5"


def test_real_lifespan_starts_and_serves_auth_status(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path, allowed_hosts="testserver"))) as client:
        assert client.get("/api/auth/status").json() == {"configured": False, "connected": False}
        assert client.get("/api/playlists").json() == []
    assert (tmp_path / "yotube.db").exists()
