from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from celery.result import AsyncResult
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import parse_session_cookie
from app.db.models import PlaylistConfig, PlaylistRun, User
from app.db.session import get_db
from app.workers.celery_app import celery_app
from app.workers.tasks import sync_discover_weekly_task
from app.schemas.playlists import (
    JobEnqueueResponse,
    JobStatusResponse,
    PlaylistRunListResponse,
    PlaylistRunOut,
    SyncDiscoverWeeklyRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/playlists", tags=["playlists"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


def _current_user(request: Request, db: Session) -> User:
    settings = get_settings()
    user_id = parse_session_cookie(request.cookies, settings.app_secret)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/sync/discover-weekly", response_model=JobEnqueueResponse)
async def sync_discover_weekly_endpoint(
    request: Request,
    body: SyncDiscoverWeeklyRequest,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    user = _current_user(request, db)
    async_result = sync_discover_weekly_task.apply_async(
        kwargs={"user_id": user.id, "dry_run": body.dry_run, "max_tracks": body.max_tracks}
    )
    return JobEnqueueResponse(job_id=async_result.id)


@router.get("/runs", response_model=PlaylistRunListResponse)
def list_runs(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")

    user = _current_user(request, db)

    runs = (
        db.query(PlaylistRun)
        .join(PlaylistConfig, PlaylistRun.playlist_config_id == PlaylistConfig.id)
        .filter(PlaylistConfig.user_id == user.id)
        .order_by(PlaylistRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return PlaylistRunListResponse(items=[PlaylistRunOut.model_validate(r) for r in runs])


@jobs_router.get("/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str):
    res = AsyncResult(job_id, app=celery_app)
    state = res.state or "PENDING"

    if state == "SUCCESS":
        payload = res.result if isinstance(res.result, dict) else {}
        return JobStatusResponse(
            job_id=job_id,
            state=state,
            status=str(payload.get("status") or "success"),
            run_id=payload.get("run_id"),
            tracks_added_count=payload.get("tracks_added_count"),
        )
    if state in {"STARTED", "RETRY", "RECEIVED", "PENDING"}:
        return JobStatusResponse(job_id=job_id, state=state, status="running")
    if state == "FAILURE":
        return JobStatusResponse(job_id=job_id, state=state, status="failed")
    return JobStatusResponse(job_id=job_id, state=state, status="unknown")

