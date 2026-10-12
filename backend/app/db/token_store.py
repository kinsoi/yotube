from sqlalchemy.orm import Session, sessionmaker

from app.db.models import OAuthToken
from app.yoto.auth import TokenSet

_TOKEN_ROW_ID = 1


class DbTokenStore:
    """Persists the single Yoto token set in SQLite."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def load(self) -> TokenSet | None:
        with self._sessions() as session:
            row = session.get(OAuthToken, _TOKEN_ROW_ID)
            if row is None:
                return None
            return TokenSet(row.access_token, row.refresh_token, row.expires_at)

    def save(self, tokens: TokenSet) -> None:
        with self._sessions.begin() as session:
            session.merge(
                OAuthToken(
                    id=_TOKEN_ROW_ID,
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token,
                    expires_at=tokens.expires_at,
                )
            )

    def clear(self) -> None:
        with self._sessions.begin() as session:
            row = session.get(OAuthToken, _TOKEN_ROW_ID)
            if row is not None:
                session.delete(row)
