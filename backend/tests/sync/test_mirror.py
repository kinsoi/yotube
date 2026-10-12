from app.db.models import Playlist, Track
from app.sync.mirror import mirror_tracks
from tests.sync.fakes import track_info


def make_playlist(session_factory, *video_ids: str) -> int:
    with session_factory.begin() as session:
        playlist = Playlist(title="Kids", source_type="youtube")
        playlist.tracks = [
            Track(video_id=v, title=f"Song {v}", position=i, icon_id=f"icon-{v}")
            for i, v in enumerate(video_ids)
        ]
        session.add(playlist)
        session.flush()
        return playlist.id


def test_mirror_reorders_reuses_rows_and_removes_missing(session_factory) -> None:
    pid = make_playlist(session_factory, "a", "b")
    with session_factory() as session:
        before = {t.video_id: t.id for t in session.get(Playlist, pid).tracks}

    with session_factory.begin() as session:
        mirror_tracks(session.get(Playlist, pid), [track_info("b"), track_info("c")])

    with session_factory() as session:
        tracks = session.get(Playlist, pid).tracks
        assert [(t.video_id, t.position) for t in tracks] == [("b", 0), ("c", 1)]
        assert tracks[0].id == before["b"]
        assert tracks[0].icon_id == "icon-b"
        assert tracks[1].status == "pending"
        assert session.query(Track).filter_by(video_id="a").count() == 0


def test_mirror_keeps_duplicates(session_factory) -> None:
    pid = make_playlist(session_factory, "a")
    with session_factory.begin() as session:
        mirror_tracks(session.get(Playlist, pid), [track_info("a"), track_info("a")])
    with session_factory() as session:
        assert [t.video_id for t in session.get(Playlist, pid).tracks] == ["a", "a"]


def test_mirror_flags_and_restores_availability(session_factory) -> None:
    pid = make_playlist(session_factory, "a")
    with session_factory.begin() as session:
        mirror_tracks(session.get(Playlist, pid), [track_info("a", available=False)])
    with session_factory() as session:
        track = session.get(Playlist, pid).tracks[0]
        assert track.status == "unavailable"
        assert track.error

    with session_factory.begin() as session:
        mirror_tracks(session.get(Playlist, pid), [track_info("a")])
    with session_factory() as session:
        track = session.get(Playlist, pid).tracks[0]
        assert (track.status, track.error) == ("pending", None)


def test_mirror_refreshes_metadata(session_factory) -> None:
    pid = make_playlist(session_factory, "a")
    with session_factory.begin() as session:
        mirror_tracks(session.get(Playlist, pid), [track_info("a")])
    with session_factory() as session:
        track = session.get(Playlist, pid).tracks[0]
        assert (track.title, track.artist, track.duration) == ("Song a", "Artist", 120)
