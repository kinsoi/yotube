import pytest

from app.youtube.models import InvalidPlaylistUrl
from app.youtube.urls import parse_playlist_id

PL = "PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"


@pytest.mark.parametrize(
    "value",
    [
        f"https://music.youtube.com/playlist?list={PL}",
        f"https://music.youtube.com/playlist?list={PL}&si=AbCdEf123",
        f"https://www.youtube.com/playlist?list={PL}",
        f"https://m.youtube.com/playlist?list={PL}",
        f"https://www.youtube.com/watch?v=dQw4w9WgXcQ&list={PL}&index=3",
        f"https://youtu.be/dQw4w9WgXcQ?list={PL}",
        f"https://music.youtube.com/browse/VL{PL}",
        f"music.youtube.com/playlist?list={PL}",
        f"  {PL}  ",
        f"VL{PL}",
    ],
)
def test_accepts_common_playlist_links(value: str) -> None:
    assert parse_playlist_id(value) == PL


def test_accepts_album_playlist_ids() -> None:
    assert parse_playlist_id("OLAK5uy_kDXyZ3bX0tnHbGCi2l0B3Ys0bDCjN0bgk") == (
        "OLAK5uy_kDXyZ3bX0tnHbGCi2l0B3Ys0bDCjN0bgk"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        f"https://evil.example.com/playlist?list={PL}",
        "https://music.youtube.com/playlist?list=bad id!",
        "not a link at all",
    ],
)
def test_rejects_non_playlist_links(value: str) -> None:
    with pytest.raises(InvalidPlaylistUrl):
        parse_playlist_id(value)
