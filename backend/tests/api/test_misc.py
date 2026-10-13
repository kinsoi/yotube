import respx

from tests.api.conftest import PREVIEW_STREAM_URL
from tests.sync.fakes import SOURCE_URL


def test_search(client) -> None:
    assert client.get("/api/search?q=lion").json()[0]["title"] == "lion song"


def test_preview_youtube_playlist(client) -> None:
    data = client.get("/api/youtube/playlist", params={"url": SOURCE_URL}).json()
    assert data["title"] == "Kids"
    assert [t["video_id"] for t in data["tracks"]] == ["a", "b"]


def test_preview_unknown_playlist_is_404(client) -> None:
    response = client.get("/api/youtube/playlist", params={"url": "PLdoesnotexist000"})
    assert (response.status_code, response.json()["code"]) == (404, "playlist_not_found")


def test_icons_search(client) -> None:
    assert client.get("/api/icons?q=lion").json() == [
        {"media_id": "m-lion", "title": "Lion", "url": "https://i/lion.png"}
    ]


def test_auth_status_login_callback_and_logout(client, services) -> None:
    assert client.get("/api/auth/status").json() == {"configured": True, "connected": True}

    login = client.get("/api/auth/login", follow_redirects=False)
    assert login.status_code == 307
    assert login.headers["location"].startswith("https://login.yotoplay.com/authorize")

    callback = client.get("/auth/callback?code=c1&state=s1", follow_redirects=False)
    assert callback.headers["location"] == "/#/settings?auth=ok"
    assert services.auth.callbacks == [("c1", "s1")]

    denied = client.get("/auth/callback?error=access_denied", follow_redirects=False)
    assert denied.headers["location"] == "/#/settings?auth=error"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/status").json()["connected"] is False


def test_settings_roundtrip(client) -> None:
    initial = client.get("/api/settings").json()
    assert initial["language"] is None
    assert initial["sync_cron"] == "0 3 * * *"
    assert client.patch("/api/settings", json={"language": "ru"}).json()["language"] == "ru"
    assert client.patch("/api/settings", json={"language": "de"}).status_code == 422


@respx.mock
def test_preview_audio_streams_the_song(client) -> None:
    respx.get(PREVIEW_STREAM_URL).respond(
        206, content=b"abc", headers={"Content-Range": "bytes 0-2/10", "Content-Length": "3"}
    )
    response = client.get("/api/preview/dQw4w9WgXcQ", headers={"Range": "bytes=0-2"})
    assert response.status_code == 206
    assert response.content == b"abc"
    assert response.headers["content-type"] == "audio/mp4"
    assert response.headers["content-range"] == "bytes 0-2/10"


def test_preview_audio_rejects_invalid_video_ids(client) -> None:
    assert client.get("/api/preview/not-a-valid-id!").status_code == 422
