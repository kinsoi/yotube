from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and `.env` in development)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    yoto_client_id: str = ""
    public_url: str = "http://localhost:8080"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    sync_cron: str = "0 3 * * *"
    tz: str = "Europe/Paris"
    data_dir: Path = Path("/data")
    static_dir: Path | None = None
    log_level: str = "INFO"
    yoto_api_url: str = "https://api.yotoplay.com"
    yoto_auth_url: str = "https://login.yotoplay.com"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'yotube.db'}"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def redirect_uri(self) -> str:
        return f"{self.public_url.rstrip('/')}/auth/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
