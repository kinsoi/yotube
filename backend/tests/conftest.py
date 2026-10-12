from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db.migrate import run_migrations
from app.db.session import make_engine, make_session_factory


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def session_factory(database_url: str) -> Iterator[sessionmaker[Session]]:
    run_migrations(database_url)
    engine = make_engine(database_url)
    yield make_session_factory(engine)
    engine.dispose()
