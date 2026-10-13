import asyncio

from app.db.models import Playlist
from tests.sync.fakes import SOURCE_URL

PL_LINK = "https://music.youtube.com/playlist?list=PLkids1234&si=abc"


def create_manual(client, **overrides):
    body = {
        "title": "Bedtime",
        "source_type": "manual",
        "tracks": [
            {
                "video_id": "songAAAAA01",
                "title": "Song a",
                "thumbnail_url": "https://i.ytimg.com/vi/a/hq.jpg",
            },
            {"video_id": "songBBBBB02", "title": "Song b"},
        ],
        **overrides,
    }
    return client.post("/api/playlists", json=body)


def test_create_manual_playlist_stores_tracks_and_starts_sync(client, services) -> None:
    response = create_manual(client)
    assert response.status_code == 201
    data = response.json()
    assert [t["video_id"] for t in data["tracks"]] == ["songAAAAA01", "songBBBBB02"]
    assert data["cover_url"] == "https://i.ytimg.com/vi/a/hq.jpg"
    assert data["auto_sync"] is False
    assert services.started == [(data["id"], False)]


def test_create_youtube_playlist_normalizes_link(client, services) -> None:
    response = client.post(
        "/api/playlists", json={"title": "Kids", "source_type": "youtube", "source_url": PL_LINK}
    )
    assert response.status_code == 201
    assert response.json()["source_url"] == "https://music.youtube.com/playlist?list=PLkids1234"
    assert response.json()["auto_sync"] is True


def test_create_with_invalid_link_is_a_friendly_400(client) -> None:
    response = client.post(
        "/api/playlists",
        json={
            "title": "Kids",
            "source_type": "youtube",
            "source_url": "https://open.spotify.com/x",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_playlist_url"


def test_create_validation_errors_have_a_code(client) -> None:
    response = client.post(
        "/api/playlists", json={"title": "X", "source_type": "manual", "tracks": []}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_list_and_get(client) -> None:
    created = create_manual(client).json()
    listed = client.get("/api/playlists").json()
    assert [p["id"] for p in listed] == [created["id"]]
    assert listed[0]["track_count"] == 2
    assert client.get(f"/api/playlists/{created['id']}").json()["title"] == "Bedtime"
    missing = client.get("/api/playlists/999")
    assert (missing.status_code, missing.json()["code"]) == (404, "not_found")


def test_update_triggers_rebuild_only_when_synced_and_relevant(client, services) -> None:
    pid = create_manual(client).json()["id"]
    services.started.clear()

    client.patch(f"/api/playlists/{pid}", json={"shuffle": True})
    assert services.started == []  # never synced: nothing to rebuild

    with services.sessions.begin() as session:
        session.get(Playlist, pid).yoto_card_id = "card-1"
    client.patch(f"/api/playlists/{pid}", json={"auto_sync": False, "color": "blue"})
    assert services.started == []
    response = client.patch(f"/api/playlists/{pid}", json={"title": "Night night"})
    assert response.json()["title"] == "Night night"
    assert services.started == [(pid, True)]


def test_replace_tracks_only_for_manual_playlists(client, services) -> None:
    pid = create_manual(client).json()["id"]
    response = client.put(
        f"/api/playlists/{pid}/tracks", json=[{"video_id": "songCCCCC03", "title": "Song c"}]
    )
    assert [t["video_id"] for t in response.json()["tracks"]] == ["songCCCCC03"]

    yt = client.post(
        "/api/playlists", json={"title": "Kids", "source_type": "youtube", "source_url": SOURCE_URL}
    ).json()
    refused = client.put(
        f"/api/playlists/{yt['id']}/tracks", json=[{"video_id": "songCCCCC03", "title": "c"}]
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "not_manual")


def test_set_track_icon_marks_it_manual(client) -> None:
    created = create_manual(client).json()
    track_id = created["tracks"][0]["id"]
    response = client.patch(
        f"/api/playlists/{created['id']}/tracks/{track_id}",
        json={"icon_id": "m-lion", "icon_url": "https://i/lion.png"},
    )
    assert response.json()["icon_manual"] is True
    missing = client.patch(
        f"/api/playlists/{created['id']}/tracks/99999", json={"icon_id": "x", "icon_url": "y"}
    )
    assert missing.status_code == 404


def test_sync_endpoint_conflicts_when_already_running(client, services) -> None:
    pid = create_manual(client).json()["id"]
    assert client.post(f"/api/playlists/{pid}/sync").status_code == 202
    services.running.add(pid)
    response = client.post(f"/api/playlists/{pid}/sync")
    assert (response.status_code, response.json()["code"]) == (409, "sync_running")


def test_reshuffle_requires_a_synced_playlist(client) -> None:
    pid = create_manual(client).json()["id"]
    response = client.post(f"/api/playlists/{pid}/reshuffle")
    assert (response.status_code, response.json()["code"]) == (409, "not_synced")


def test_delete_optionally_removes_yoto_content(client, services) -> None:
    pid = create_manual(client).json()["id"]
    with services.sessions.begin() as session:
        session.get(Playlist, pid).yoto_card_id = "card-9"
    assert client.delete(f"/api/playlists/{pid}?delete_on_yoto=true").status_code == 204
    assert services.yoto.deleted_cards == ["card-9"]
    assert client.get(f"/api/playlists/{pid}").status_code == 404


def test_real_background_sync_runs_and_publishes_events(real_client, real_services) -> None:
    events: list[dict] = []

    # Subscribe before the request: the broker only delivers to live subscribers.
    import asyncio

    portal_loop = real_client.portal  # anyio blocking portal bound to the app loop
    assert portal_loop is not None
    queue_cm = real_services.broker.subscribe()
    queue = portal_loop.call(queue_cm.__aenter__)
    try:
        response = create_manual(real_client)
        assert response.status_code == 201
        pid = response.json()["id"]

        async def wait() -> None:
            await asyncio.gather(*list(real_services._tasks))

        portal_loop.call(wait)
        while not queue.empty():
            events.append(queue.get_nowait())
    finally:
        portal_loop.call(queue_cm.__aexit__, None, None, None)

    detail = real_client.get(f"/api/playlists/{pid}").json()
    assert detail["last_sync_status"] == "ok"
    assert detail["yoto_card_id"]
    types = [e["type"] for e in events]
    assert "progress" in types
    assert {"type": "playlist_updated", "playlist_id": pid} in events


def test_delete_keeps_playlist_when_yoto_deletion_fails(client, services) -> None:
    from app.yoto.errors import YotoError

    async def boom(card_id: str) -> None:
        raise YotoError("nope")

    services.yoto.delete_content = boom  # type: ignore[method-assign]
    pid = create_manual(client).json()["id"]
    with services.sessions.begin() as session:
        session.get(Playlist, pid).yoto_card_id = "card-9"
    response = client.delete(f"/api/playlists/{pid}?delete_on_yoto=true")
    assert (response.status_code, response.json()["code"]) == (502, "yoto_error")
    assert client.get(f"/api/playlists/{pid}").status_code == 200


def test_manual_cover_ignores_non_allowed_thumbnail_hosts(client) -> None:
    tracks = [
        {"video_id": "songAAAAA01", "title": "A", "thumbnail_url": "http://169.254.169.254/x.jpg"},
        {"video_id": "songBBBBB02", "title": "B", "thumbnail_url": "https://yt3.ggpht.com/b.jpg"},
    ]
    assert create_manual(client, tracks=tracks).json()["cover_url"] == "https://yt3.ggpht.com/b.jpg"
    bad = create_manual(client, tracks=tracks[:1]).json()
    assert bad["cover_url"] is None


def _wait_for_tasks(portal, services) -> None:
    async def wait() -> None:
        while services._tasks:
            await asyncio.gather(*list(services._tasks))

    portal.call(wait)


def test_edit_during_a_running_sync_triggers_a_second_run(real_client, real_services) -> None:
    portal = real_client.portal
    assert portal is not None
    yoto = real_services.yoto
    gate = None

    async def block_first_save() -> None:
        nonlocal gate
        gate = asyncio.Event()
        original = yoto.save_content

        async def gated(body, card_id):
            if len(yoto.saved) == 0:
                await gate.wait()
            return await original(body, card_id)

        yoto.save_content = gated

    portal.call(block_first_save)
    pid = create_manual(real_client).json()["id"]
    for _ in range(3):  # let the background sync reach the gate
        portal.call(asyncio.sleep, 0)
    assert real_services.engine.is_running(pid)

    # edits while the first sync is in flight: queued, not dropped
    new_tracks = [{"video_id": "songZZZZZ26", "title": "Song z"}]
    assert real_client.put(f"/api/playlists/{pid}/tracks", json=new_tracks).status_code == 200
    assert real_services._pending == {pid: False}
    # the explicit endpoint still reports the conflict
    assert real_client.post(f"/api/playlists/{pid}/sync").status_code == 409

    portal.call(gate.set)
    _wait_for_tasks(portal, real_services)

    assert len(yoto.saved) == 2
    assert yoto.chapter_titles() == ["Song z"]
    assert real_services._pending == {}


def test_queued_requests_merge_with_full_sync_winning(real_services) -> None:
    real_services.engine._running.add(1)  # a sync is in progress
    real_services.request_sync(1, rebuild=True)
    assert real_services._pending == {1: True}
    real_services.request_sync(1, rebuild=False)
    assert real_services._pending == {1: False}
    real_services.request_sync(1, rebuild=True)
    assert real_services._pending == {1: False}


def test_track_video_ids_must_be_youtube_ids(client) -> None:
    bad = [{"video_id": "dQw4w9WgXcQ/../../x", "title": "Evil"}]
    response = create_manual(client, tracks=bad)
    assert (response.status_code, response.json()["code"]) == (422, "validation_error")
    pid = create_manual(client).json()["id"]
    refused = client.put(f"/api/playlists/{pid}/tracks", json=bad)
    assert (refused.status_code, refused.json()["code"]) == (422, "validation_error")
