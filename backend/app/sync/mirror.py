from collections import defaultdict
from collections.abc import Sequence

from app.db.models import Playlist, Track
from app.youtube.models import TrackInfo

UNAVAILABLE_MESSAGE = "No longer available on YouTube"


def mirror_tracks(playlist: Playlist, source: Sequence[TrackInfo]) -> None:
    """Make `playlist.tracks` match `source` exactly (order, duplicates, removals).

    Existing rows are reused for videos already in the playlist so their icon and
    upload status survive; rows whose video left the source are deleted (delete-orphan).
    """
    reusable: dict[str, list[Track]] = defaultdict(list)
    for track in sorted(playlist.tracks, key=lambda t: t.position):
        reusable[track.video_id].append(track)

    mirrored: list[Track] = []
    for position, info in enumerate(source):
        candidates = reusable[info.video_id]
        track = candidates.pop(0) if candidates else Track(video_id=info.video_id, status="pending")
        track.title = info.title
        track.artist = info.artist
        track.duration = info.duration
        track.thumbnail_url = info.thumbnail_url
        track.position = position
        if not info.available:
            track.status, track.error = "unavailable", UNAVAILABLE_MESSAGE
        elif track.status == "unavailable":
            track.status, track.error = "pending", None
        mirrored.append(track)

    playlist.tracks = mirrored
