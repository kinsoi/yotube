from dataclasses import dataclass


@dataclass(frozen=True)
class UploadedAudio:
    sha256: str
    duration: int
    file_size: int
    channels: str
    format: str


@dataclass(frozen=True)
class Icon:
    media_id: str
    title: str
    url: str
    tags: tuple[str, ...] = ()
