"""SQLAlchemy models. ORM only (parameterized SQL); never log or expose token fields (CWE-532)."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spotify_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    oauth_tokens: Mapped[list["OAuthToken"]] = relationship("OAuthToken", back_populates="user", cascade="all, delete-orphan")
    playlist_configs: Mapped[list["PlaylistConfig"]] = relationship("PlaylistConfig", back_populates="user", cascade="all, delete-orphan")


class OAuthToken(Base):
    """Tokens must never appear in __repr__, logs, or API responses (CWE-532)."""
    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scope: Mapped[str] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="oauth_tokens")

    def __repr__(self) -> str:
        return f"OAuthToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})"


class PlaylistConfig(Base):
    __tablename__ = "playlist_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_playlist_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_playlist_id: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="playlist_configs")
    runs: Mapped[list["PlaylistRun"]] = relationship("PlaylistRun", back_populates="playlist_config", cascade="all, delete-orphan")


class PlaylistRun(Base):
    __tablename__ = "playlist_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playlist_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracks_added_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    playlist_config: Mapped["PlaylistConfig"] = relationship("PlaylistConfig", back_populates="runs")

    __table_args__ = (Index("ix_playlist_runs_config_started", "playlist_config_id", "started_at"),)
