from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.timeutil import utcnow


class Base(DeclarativeBase):
    pass


class Playlist(Base):
    __tablename__ = "playlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(16))  # "youtube" | "manual"
    source_url: Mapped[str | None] = mapped_column(String(500))
    yoto_card_id: Mapped[str | None] = mapped_column(String(64))
    shuffle: Mapped[bool] = mapped_column(default=False)
    auto_sync: Mapped[bool] = mapped_column(default=True)
    color: Mapped[str] = mapped_column(String(16), default="orange")
    cover_url: Mapped[str | None] = mapped_column(String(500))
    yoto_cover_url: Mapped[str | None] = mapped_column(String(500))
    last_sync_at: Mapped[datetime | None]
    last_sync_status: Mapped[str | None] = mapped_column(String(16))
    last_sync_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="playlist",
        order_by="Track.position",
        cascade="all, delete-orphan",
    )


class Track(Base):
    __tablename__ = "track"

    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlist.id", ondelete="CASCADE"), index=True
    )
    video_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(300))
    artist: Mapped[str] = mapped_column(String(300), default="")
    duration: Mapped[int | None]
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[int]
    icon_id: Mapped[str | None] = mapped_column(String(64))
    icon_url: Mapped[str | None] = mapped_column(String(500))
    icon_manual: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error: Mapped[str | None] = mapped_column(String(500))

    playlist: Mapped[Playlist] = relationship(back_populates="tracks")


class UploadedMedia(Base):
    """Global cache: one Yoto upload per YouTube video, shared by all playlists."""

    __tablename__ = "uploaded_media"

    video_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(128))
    duration: Mapped[int]
    file_size: Mapped[int]
    channels: Mapped[str] = mapped_column(String(16))
    format: Mapped[str] = mapped_column(String(16))
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)


class OAuthToken(Base):
    __tablename__ = "oauth_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime]


class AppSetting(Base):
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))
