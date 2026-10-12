import re
from urllib.parse import parse_qs, urlparse

from app.youtube.models import InvalidPlaylistUrl

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,80}$")
_HOSTS = frozenset(
    {"music.youtube.com", "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}
)
_IMAGE_HOSTS = frozenset(
    {"i.ytimg.com", "yt3.ggpht.com", "yt3.googleusercontent.com", "lh3.googleusercontent.com"}
)
_IMAGE_SUFFIXES = (".googleusercontent.com", ".ytimg.com")


def is_allowed_image_url(value: str | None) -> bool:
    """True only for https thumbnail URLs on YouTube's image hosts (guards server-side fetches)."""
    if not value:
        return False
    try:
        parsed = urlparse(value)
        host = parsed.hostname
        parsed.port  # noqa: B018  (raises ValueError on a malformed port)
    except ValueError:
        return False
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    return host in _IMAGE_HOSTS or host.endswith(_IMAGE_SUFFIXES)


def parse_playlist_id(value: str) -> str:
    """Extract a playlist id from a YouTube / YouTube Music link or a bare id."""
    text = value.strip()
    if not text:
        raise InvalidPlaylistUrl("The playlist link is empty")

    if "/" not in text and "?" not in text:
        candidate = text
    else:
        url = urlparse(text if "://" in text else f"https://{text}")
        if url.hostname not in _HOSTS:
            raise InvalidPlaylistUrl("This is not a YouTube Music link")
        query = parse_qs(url.query)
        if "list" in query:
            candidate = query["list"][0]
        elif url.path.startswith("/browse/"):
            candidate = url.path.removeprefix("/browse/")
        else:
            raise InvalidPlaylistUrl("This link does not point to a playlist")

    if candidate.startswith("VL"):
        candidate = candidate[2:]
    if not _ID_RE.match(candidate):
        raise InvalidPlaylistUrl("This link does not contain a valid playlist id")
    return candidate
