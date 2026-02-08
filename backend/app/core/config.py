"""Load config from env; fail fast if required vars missing (CWE-798). No secrets in code."""
from __future__ import annotations

from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding="utf-8",
        # Pydantic Settings tries to JSON-decode "complex" env values (like list[str]).
        # We want to accept a simple comma-separated string for ALLOWED_ORIGINS.
        enable_decoding=False,
    )

    # Required for OAuth and app security
    client_id: str = Field(..., min_length=1, alias="SPOTIFY_CLIENT_ID")
    client_secret: str = Field(..., min_length=1, alias="SPOTIFY_CLIENT_SECRET")
    app_secret: str = Field(..., min_length=16, alias="APP_SECRET")
    database_url: str = Field(..., alias="DATABASE_URL")
    base_url: str = Field(..., alias="BASE_URL")

    # CORS; comma-separated in env
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        alias="ALLOWED_ORIGINS",
    )

    app_name: str = Field(default="Spotify Playlist Manager", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    json_logs: bool = Field(default=False, alias="JSON_LOGS")
    auth_success_redirect: str | None = Field(default=None, alias="AUTH_SUCCESS_REDIRECT")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v.strip():
                return ["http://localhost:3000"]
            return [x.strip() for x in v.split(",") if x.strip()]
        return ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Cached settings; raises ValidationError if required env vars are missing."""
    return Settings()
