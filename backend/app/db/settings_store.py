from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AppSetting


class DbSettingsStore:
    """Small key/value store for app-level settings (UI language, cached icon ids…)."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def get(self, key: str) -> str | None:
        with self._sessions() as session:
            setting = session.get(AppSetting, key)
            return setting.value if setting else None

    def set(self, key: str, value: str) -> None:
        with self._sessions.begin() as session:
            session.merge(AppSetting(key=key, value=value))
