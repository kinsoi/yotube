from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Color = Literal["orange", "yellow", "blue", "green", "pink", "purple", "red", "teal"]
Language = Literal["en", "fr", "ru"]


class TrackIn(BaseModel):
    video_id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=300)
    artist: str = Field(default="", max_length=300)
    duration: int | None = Field(default=None, ge=0)
    thumbnail_url: str | None = Field(default=None, max_length=500)


class TrackInfoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    title: str
    artist: str
    duration: int | None
    thumbnail_url: str | None
    available: bool = True


class PlaylistPreview(BaseModel):
    playlist_id: str
    title: str
    thumbnail_url: str | None
    tracks: list[TrackInfoOut]


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: str
    title: str
    artist: str
    duration: int | None
    thumbnail_url: str | None
    position: int
    icon_id: str | None
    icon_url: str | None
    icon_manual: bool
    status: str
    error: str | None


class PlaylistSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: str
    source_url: str | None
    yoto_card_id: str | None
    shuffle: bool
    auto_sync: bool
    color: str
    cover_url: str | None
    last_sync_at: datetime | None
    last_sync_status: str | None
    last_sync_error: str | None
    track_count: int
    syncing: bool
    icon_urls: list[str]


class PlaylistDetail(PlaylistSummary):
    tracks: list[TrackOut]


class PlaylistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_type: Literal["youtube", "manual"]
    source_url: str | None = Field(default=None, max_length=500)
    tracks: list[TrackIn] = Field(default_factory=list, max_length=500)
    shuffle: bool = False
    auto_sync: bool = True
    color: Color = "orange"

    @model_validator(mode="after")
    def check_source(self) -> "PlaylistCreate":
        if self.source_type == "youtube" and not self.source_url:
            raise ValueError("source_url is required for a YouTube Music playlist")
        if self.source_type == "manual" and not self.tracks:
            raise ValueError("A hand-picked playlist needs at least one track")
        return self


class PlaylistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    shuffle: bool | None = None
    auto_sync: bool | None = None
    color: Color | None = None


class TrackIconUpdate(BaseModel):
    icon_id: str = Field(min_length=1, max_length=64)
    icon_url: str = Field(min_length=1, max_length=500)


class IconOut(BaseModel):
    media_id: str
    title: str
    url: str


class AuthStatus(BaseModel):
    configured: bool
    connected: bool


class SettingsOut(BaseModel):
    language: Language | None
    sync_cron: str
    timezone: str
    icon_ai_enabled: bool
    yoto_configured: bool
    yoto_connected: bool


class SettingsUpdate(BaseModel):
    language: Language


class Accepted(BaseModel):
    status: Literal["started"] = "started"
