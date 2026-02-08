from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SyncDiscoverWeeklyRequest(BaseModel):
    dry_run: bool = Field(default=False)
    max_tracks: int | None = Field(default=None, ge=1, le=500)


class JobEnqueueResponse(BaseModel):
    job_id: str


class PlaylistRunOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    playlist_config_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    tracks_added_count: int | None
    error_message: str | None


class PlaylistRunListResponse(BaseModel):
    items: list[PlaylistRunOut]


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    status: str
    run_id: int | None = None
    tracks_added_count: int | None = None

