from datetime import datetime

from app.db.token_store import DbTokenStore
from app.yoto.auth import TokenSet


def test_token_store_roundtrip(session_factory) -> None:
    store = DbTokenStore(session_factory)
    assert store.load() is None

    first = TokenSet("a1", "r1", datetime(2026, 10, 12, 13, 0))
    store.save(first)
    second = TokenSet("a2", "r2", datetime(2026, 10, 12, 14, 0))
    store.save(second)
    assert store.load() == second

    store.clear()
    assert store.load() is None
