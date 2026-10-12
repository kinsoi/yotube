import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import respx

from app.yoto.client import YotoClient
from app.yoto.errors import AuthRequired, ContentNotFound, YotoError
from app.yoto.models import Icon, UploadedAudio

API = "https://api.yotoplay.com"
UPLOAD_URL = "https://uploads.example.com/put-here"


class StaticTokens:
    async def access_token(self) -> str:
        return "tok"


async def no_sleep(_seconds: float) -> None:
    return None


@pytest.fixture
async def client() -> AsyncIterator[YotoClient]:
    async with httpx.AsyncClient() as http:
        yield YotoClient(StaticTokens(), http, API, poll_attempts=3, sleep=no_sleep)


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "song.m4a"
    path.write_bytes(b"fake-audio")
    return path


def mock_upload_url(upload_url: str | None = UPLOAD_URL) -> None:
    respx.get(f"{API}/media/transcode/audio/uploadUrl").mock(
        return_value=httpx.Response(
            200, json={"upload": {"uploadUrl": upload_url, "uploadId": "up-1"}}
        )
    )


TRANSCODED = {
    "transcode": {
        "transcodedSha256": "sha-abc",
        "transcodedInfo": {
            "duration": 183.4,
            "fileSize": 2048,
            "channels": "stereo",
            "format": "aac",
        },
    }
}


@respx.mock
async def test_upload_audio_puts_file_and_polls_until_transcoded(client, audio_file) -> None:
    mock_upload_url()
    put = respx.put(UPLOAD_URL).mock(return_value=httpx.Response(200))
    respx.get(f"{API}/media/upload/up-1/transcoded").mock(
        side_effect=[
            httpx.Response(200, json={"transcode": {}}),
            httpx.Response(200, json=TRANSCODED),
        ]
    )

    result = await client.upload_audio(audio_file, "audio/mp4")

    assert result == UploadedAudio("sha-abc", 183, 2048, "stereo", "aac")
    assert put.calls.last.request.content == b"fake-audio"
    assert put.calls.last.request.headers["Content-Type"] == "audio/mp4"
    assert "authorization" not in put.calls.last.request.headers


@respx.mock
async def test_upload_audio_skips_put_when_yoto_already_has_file(client, audio_file) -> None:
    mock_upload_url(upload_url=None)
    respx.get(f"{API}/media/upload/up-1/transcoded").mock(
        return_value=httpx.Response(200, json=TRANSCODED)
    )
    assert (await client.upload_audio(audio_file, "audio/mp4")).sha256 == "sha-abc"


@respx.mock
async def test_upload_audio_times_out_when_transcoding_never_finishes(client, audio_file) -> None:
    mock_upload_url()
    respx.put(UPLOAD_URL).mock(return_value=httpx.Response(200))
    respx.get(f"{API}/media/upload/up-1/transcoded").mock(
        return_value=httpx.Response(200, json={"transcode": {}})
    )
    with pytest.raises(YotoError, match="transcoding"):
        await client.upload_audio(audio_file, "audio/mp4")


@respx.mock
async def test_requests_send_bearer_token_and_retry_server_errors(client) -> None:
    route = respx.get(f"{API}/media/displayIcons/user/yoto").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"displayIcons": []})]
    )
    assert await client.list_public_icons() == []
    assert route.call_count == 2
    assert route.calls.last.request.headers["Authorization"] == "Bearer tok"


@respx.mock
async def test_unauthorized_response_raises_auth_required(client) -> None:
    respx.get(f"{API}/media/displayIcons/user/yoto").mock(return_value=httpx.Response(401))
    with pytest.raises(AuthRequired):
        await client.list_public_icons()


@respx.mock
async def test_list_public_icons_maps_fields(client) -> None:
    respx.get(f"{API}/media/displayIcons/user/yoto").mock(
        return_value=httpx.Response(
            200,
            json={
                "displayIcons": [
                    {
                        "mediaId": "m1",
                        "title": "Lion",
                        "url": "https://i/1.png",
                        "publicTags": ["animal", "lion"],
                    },
                    {"mediaId": "m2", "url": "https://i/2.png"},
                ]
            },
        )
    )
    assert await client.list_public_icons() == [
        Icon("m1", "Lion", "https://i/1.png", ("animal", "lion")),
        Icon("m2", "", "https://i/2.png", ()),
    ]


@respx.mock
async def test_upload_icon_sends_multipart_file(client) -> None:
    route = respx.post(f"{API}/media/displayIcons/user/me/upload").mock(
        return_value=httpx.Response(
            200, json={"displayIcon": {"mediaId": "m9", "url": "https://i/9.png"}}
        )
    )
    icon = await client.upload_icon(b"\x89PNG", "note.png")
    assert icon == Icon("m9", "note.png", "https://i/9.png")
    request = route.calls.last.request
    assert request.url.params["autoConvert"] == "true"
    assert b'name="file"' in request.content


@respx.mock
async def test_upload_cover_from_url_downloads_then_uploads(client) -> None:
    respx.get("https://img.example.com/cover.jpg").mock(
        return_value=httpx.Response(200, content=b"jpeg", headers={"Content-Type": "image/jpeg"})
    )
    route = respx.post(f"{API}/media/coverImage/user/me/upload").mock(
        return_value=httpx.Response(
            200, json={"coverImage": {"mediaId": "c1", "mediaUrl": "https://cdn/c1.jpg"}}
        )
    )
    assert (
        await client.upload_cover_from_url("https://img.example.com/cover.jpg")
        == "https://cdn/c1.jpg"
    )
    assert route.calls.last.request.content == b"jpeg"
    assert route.calls.last.request.url.params["autoconvert"] == "true"


@respx.mock
async def test_save_content_creates_then_updates_with_card_id(client) -> None:
    route = respx.post(f"{API}/content").mock(
        return_value=httpx.Response(200, json={"card": {"cardId": "card-1"}})
    )
    assert await client.save_content({"title": "T"}, None) == "card-1"
    assert "cardId" not in json.loads(route.calls.last.request.content)

    assert await client.save_content({"title": "T"}, "card-1") == "card-1"
    assert json.loads(route.calls.last.request.content)["cardId"] == "card-1"


@respx.mock
async def test_save_content_raises_content_not_found_for_deleted_card(client) -> None:
    respx.post(f"{API}/content").mock(
        return_value=httpx.Response(400, json={"error": {"code": "x"}})
    )
    respx.get(f"{API}/content/gone").mock(return_value=httpx.Response(404))
    with pytest.raises(ContentNotFound):
        await client.save_content({"title": "T"}, "gone")


@respx.mock
async def test_save_content_validation_error_on_existing_card_is_a_yoto_error(client) -> None:
    respx.post(f"{API}/content").mock(return_value=httpx.Response(400, json={"error": "bad"}))
    respx.get(f"{API}/content/card-1").mock(
        return_value=httpx.Response(200, json={"card": {"cardId": "card-1"}})
    )
    with pytest.raises(YotoError) as excinfo:
        await client.save_content({"title": "T"}, "card-1")
    assert not isinstance(excinfo.value, ContentNotFound)


@respx.mock
async def test_delete_content_ignores_missing_card(client) -> None:
    respx.delete(f"{API}/content/gone").mock(return_value=httpx.Response(404))
    await client.delete_content("gone")
