from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal

Phase = Literal["fetching", "uploading", "icons", "saving", "done", "error"]


@dataclass(frozen=True)
class SyncProgress:
    playlist_id: int
    phase: Phase
    current: int = 0
    total: int = 0
    track_title: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ProgressCallback = Callable[[SyncProgress], None]
