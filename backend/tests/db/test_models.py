from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import select

from app.db.models import Base, Playlist, Track
from app.db.session import make_engine
from app.db.settings_store import DbSettingsStore


def test_migrations_match_models(database_url, session_factory) -> None:
    engine = make_engine(database_url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []


def test_tracks_are_ordered_and_deleted_with_playlist(session_factory) -> None:
    with session_factory.begin() as session:
        playlist = Playlist(title="Kids", source_type="manual")
        playlist.tracks = [
            Track(video_id="b", title="B", position=1),
            Track(video_id="a", title="A", position=0),
        ]
        session.add(playlist)

    with session_factory() as session:
        playlist = session.scalars(select(Playlist)).one()
        assert [t.video_id for t in playlist.tracks] == ["a", "b"]
        assert playlist.tracks[0].status == "pending"
        session.delete(playlist)
        session.commit()
        assert session.scalars(select(Track)).all() == []


def test_settings_store_roundtrip(session_factory) -> None:
    store = DbSettingsStore(session_factory)
    assert store.get("language") is None
    store.set("language", "fr")
    store.set("language", "ru")
    assert store.get("language") == "ru"
