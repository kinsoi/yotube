import asyncio
import random

import pytest
from sqlalchemy import select

from app.db.models import Playlist, Track
from app.sync.engine import SyncAlreadyRunning, SyncEngine, reset_interrupted
from app.sync.progress import SyncProgress
from app.yoto.content import MAX_CHAPTERS
from app.yoto.errors import AuthRequired
from tests.sync.fakes import SOURCE_URL, FakeIcons, FakeMusic, FakeYoto, playlist_info


async def no_sleep(_seconds: float) -> None:
    return None


@pytest.fixture
def music(tmp_path) -> FakeMusic:
    fake = FakeMusic(tmp_path)
    fake.playlists[SOURCE_URL] = playlist_info("a", "b", "c")
    return fake


@pytest.fixture
def yoto() -> FakeYoto:
    return FakeYoto()


@pytest.fixture
def icons() -> FakeIcons:
    return FakeIcons()


@pytest.fixture
def engine(session_factory, music, yoto, icons) -> SyncEngine:
    return SyncEngine(
        session_factory,
        music,
        yoto,
        icons,
        rng=random.Random(1),
        retry_delays=(0, 0),
        sleep=no_sleep,
    )


def add_playlist(session_factory, tracks: list[str] | None = None, **fields) -> int:
    values = {"title": "Kids", "source_type": "youtube", "source_url": SOURCE_URL, **fields}
    with session_factory.begin() as session:
        playlist = Playlist(**values)
        playlist.tracks = [
            Track(video_id=v, title=f"Song {v}", position=i) for i, v in enumerate(tracks or [])
        ]
        session.add(playlist)
        session.flush()
        return playlist.id


def load(session_factory, pid: int) -> Playlist:
    with session_factory() as session:
        playlist = session.get(Playlist, pid)
        assert playlist is not None
        _ = playlist.tracks  # load before the session closes
        return playlist


async def test_first_sync_uploads_tracks_and_creates_yoto_playlist(
    engine, session_factory, music, yoto
) -> None:
    pid = add_playlist(session_factory)

    result = await engine.sync(pid)

    assert (result.status, result.uploaded, result.failed) == ("ok", 3, 0)
    assert sorted(yoto.uploads) == ["a", "b", "c"]
    assert yoto.chapter_titles() == ["Song a", "Song b", "Song c"]
    playlist = load(session_factory, pid)
    assert playlist.yoto_card_id == "card-1"
    assert playlist.last_sync_status == "ok"
    assert playlist.last_sync_at is not None
    assert playlist.yoto_cover_url == "https://cdn/cover1.jpg"
    assert [t.status for t in playlist.tracks] == ["uploaded"] * 3
    assert playlist.tracks[0].icon_id == "icon-Song a"
    assert not any(path.exists() for path in music.files)


async def test_resync_mirrors_changes_and_only_uploads_new_tracks(
    engine, session_factory, music, yoto, icons
) -> None:
    pid = add_playlist(session_factory)
    await engine.sync(pid)
    music.playlists[SOURCE_URL] = playlist_info("c", "a", "d")
    yoto.uploads.clear()

    result = await engine.sync(pid)

    assert result.status == "ok"
    assert yoto.uploads == ["d"]
    assert yoto.chapter_titles() == ["Song c", "Song a", "Song d"]
    assert yoto.saved[-1][1] == "card-1"
    assert [t.video_id for t in load(session_factory, pid).tracks] == ["c", "a", "d"]
    assert icons.calls == ["Song a", "Song b", "Song c", "Song d"]


async def test_duplicate_video_uploaded_once_but_kept_twice(
    engine, session_factory, music, yoto
) -> None:
    music.playlists[SOURCE_URL] = playlist_info("a", "b", "a")
    pid = add_playlist(session_factory)

    await engine.sync(pid)

    assert sorted(yoto.uploads) == ["a", "b"]
    assert yoto.chapter_titles() == ["Song a", "Song b", "Song a"]


async def test_media_cache_is_shared_between_playlists(engine, session_factory, yoto) -> None:
    await engine.sync(add_playlist(session_factory))
    other = add_playlist(
        session_factory, tracks=["b"], title="Other", source_type="manual", source_url=None
    )

    result = await engine.sync(other)

    assert result.status == "ok"
    assert len(yoto.uploads) == 3
    assert yoto.chapter_titles() == ["Song b"]


async def test_unavailable_track_is_skipped_and_reported(
    engine, session_factory, music, yoto
) -> None:
    music.unavailable = {"b"}
    pid = add_playlist(session_factory)

    result = await engine.sync(pid)

    assert (result.status, result.failed) == ("partial", 1)
    assert music.downloads.count("b") == 1  # permanent errors are not retried
    assert yoto.chapter_titles() == ["Song a", "Song c"]
    track_b = load(session_factory, pid).tracks[1]
    assert track_b.status == "unavailable"
    assert "unavailable" in (track_b.error or "")


async def test_track_removed_from_youtube_keeps_uploaded_copy(
    engine, session_factory, music, yoto
) -> None:
    pid = add_playlist(session_factory)
    await engine.sync(pid)
    music.playlists[SOURCE_URL] = playlist_info("a", "b", "c", unavailable=("b",))

    result = await engine.sync(pid)

    assert result.status == "ok"
    assert yoto.chapter_titles() == ["Song a", "Song b", "Song c"]
    assert load(session_factory, pid).tracks[1].status == "unavailable"


async def test_track_unavailable_from_failed_download_is_retried_next_sync(
    engine, session_factory, music
) -> None:
    pid = add_playlist(session_factory, tracks=["a"], source_type="manual", source_url=None)
    music.unavailable = {"a"}

    first = await engine.sync(pid)

    assert first.status == "error"
    assert load(session_factory, pid).tracks[0].status == "unavailable"

    music.unavailable = set()
    second = await engine.sync(pid)

    assert second.status == "ok"
    assert music.downloads.count("a") == 2
    assert load(session_factory, pid).tracks[0].status == "uploaded"
    assert load(session_factory, pid).last_sync_status == "ok"


async def test_transient_download_failures_are_retried(engine, session_factory, music) -> None:
    music.flaky = {"a": 2}
    result = await engine.sync(add_playlist(session_factory))
    assert result.status == "ok"
    assert music.downloads.count("a") == 3


async def test_persistent_download_failure_marks_track_as_error(
    engine, session_factory, music
) -> None:
    music.flaky = {"a": 10}
    pid = add_playlist(session_factory)
    result = await engine.sync(pid)
    assert (result.status, result.failed) == ("partial", 1)
    assert load(session_factory, pid).tracks[0].status == "error"


async def test_deleted_yoto_card_is_recreated(engine, session_factory, yoto) -> None:
    pid = add_playlist(session_factory)
    await engine.sync(pid)
    yoto.deleted.add("card-1")

    result = await engine.sync(pid)

    assert result.status == "ok"
    assert load(session_factory, pid).yoto_card_id == "card-2"


async def test_empty_source_fails_without_touching_yoto(
    engine, session_factory, music, yoto
) -> None:
    pid = add_playlist(session_factory)
    await engine.sync(pid)
    music.playlists[SOURCE_URL] = playlist_info()

    result = await engine.sync(pid)

    assert result.status == "error"
    assert len(yoto.saved) == 1
    playlist = load(session_factory, pid)
    assert playlist.yoto_card_id == "card-1"
    assert len(playlist.tracks) == 3
    assert playlist.last_sync_status == "error"
    assert "empty" in (playlist.last_sync_error or "")


async def test_private_source_playlist_fails_cleanly(engine, session_factory, music, yoto) -> None:
    music.playlists.clear()
    pid = add_playlist(session_factory)

    result = await engine.sync(pid)

    assert result.status == "error"
    assert yoto.saved == []
    assert "Could not read playlist" in (load(session_factory, pid).last_sync_error or "")


async def test_shuffle_randomizes_order_and_enables_player_shuffle(
    engine, session_factory, music, yoto
) -> None:
    ids = ["a", "b", "c", "d", "e", "f"]
    music.playlists[SOURCE_URL] = playlist_info(*ids)
    pid = add_playlist(session_factory, shuffle=True)

    await engine.sync(pid)

    titles = yoto.chapter_titles()
    expected = [f"Song {v}" for v in ids]
    assert sorted(titles) == expected
    assert titles != expected  # deterministic with random.Random(1)
    assert yoto.saved[-1][0]["content"]["config"]["shuffle"] == [{"start": 0, "end": 5, "limit": 6}]


async def test_more_than_100_tracks_is_partial_and_capped(
    engine, session_factory, music, yoto
) -> None:
    music.playlists[SOURCE_URL] = playlist_info(*(f"v{n}" for n in range(MAX_CHAPTERS + 1)))
    result = await engine.sync(add_playlist(session_factory))
    assert result.status == "partial"
    assert len(yoto.chapter_titles()) == MAX_CHAPTERS


async def test_auth_expiry_propagates_and_marks_error(engine, session_factory, yoto) -> None:
    yoto.auth_expired = True
    pid = add_playlist(session_factory)
    with pytest.raises(AuthRequired):
        await engine.sync(pid)
    assert load(session_factory, pid).last_sync_status == "error"
    assert not engine.is_running(pid)


async def test_concurrent_sync_of_same_playlist_is_rejected(engine, session_factory, music) -> None:
    music.gate = asyncio.Event()
    pid = add_playlist(session_factory)
    first = asyncio.create_task(engine.sync(pid))
    for _ in range(5):
        await asyncio.sleep(0)

    assert engine.is_running(pid)
    with pytest.raises(SyncAlreadyRunning):
        await engine.sync(pid)
    assert load(session_factory, pid).last_sync_status == "running"

    music.gate.set()
    assert (await first).status == "ok"


async def test_manual_icon_is_never_replaced(engine, session_factory, icons) -> None:
    pid = add_playlist(session_factory, tracks=["a", "b"], source_type="manual", source_url=None)
    with session_factory.begin() as session:
        track = session.scalars(select(Track).where(Track.video_id == "a")).one()
        track.icon_id, track.icon_manual = "mine", True

    await engine.sync(pid)

    assert load(session_factory, pid).tracks[0].icon_id == "mine"
    assert icons.calls == ["Song b"]


async def test_manual_playlist_sync_does_not_read_youtube(engine, session_factory, music) -> None:
    pid = add_playlist(session_factory, tracks=["a"], source_type="manual", source_url=None)
    assert (await engine.sync(pid)).status == "ok"
    assert music.fetches == 0


async def test_rebuild_saves_content_without_fetching_or_uploading(
    engine, session_factory, music, yoto
) -> None:
    pid = add_playlist(session_factory)
    await engine.sync(pid)
    with session_factory.begin() as session:
        session.get(Playlist, pid).title = "Renamed"

    result = await engine.rebuild(pid)

    assert result.status == "ok"
    assert music.fetches == 1
    assert len(yoto.uploads) == 3
    assert yoto.saved[-1][0]["title"] == "Renamed"
    assert yoto.saved[-1][1] == "card-1"


async def test_cover_is_uploaded_only_once(engine, session_factory, yoto) -> None:
    pid = add_playlist(session_factory)
    await engine.sync(pid)
    await engine.sync(pid)
    assert yoto.covers == ["https://t/pl.jpg"]


async def test_progress_reports_each_phase_in_order(engine, session_factory) -> None:
    events: list[SyncProgress] = []
    await engine.sync(add_playlist(session_factory), events.append)

    phases = list(dict.fromkeys(e.phase for e in events))
    assert phases == ["fetching", "uploading", "icons", "saving", "done"]
    final_upload = [e for e in events if e.phase == "uploading"][-1]
    assert (final_upload.current, final_upload.total) == (3, 3)


async def test_missing_playlist_returns_error(engine) -> None:
    assert (await engine.sync(999)).status == "error"


def test_reset_interrupted_marks_running_playlists_as_error(session_factory) -> None:
    pid = add_playlist(session_factory, last_sync_status="running")
    assert reset_interrupted(session_factory) == 1
    playlist = load(session_factory, pid)
    assert playlist.last_sync_status == "error"
    assert "Interrupted" in (playlist.last_sync_error or "")
