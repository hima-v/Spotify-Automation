from __future__ import annotations

import asyncio
import logging

from celery import Task

from app.core.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal
from app.playlists.service import SpotifyApiError, sync_discover_weekly
from app.schemas.playlists import SyncDiscoverWeeklyRequest
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(bind=True, name="sync.discover_weekly", max_retries=5)
def sync_discover_weekly_task(self: Task, *, user_id: int, dry_run: bool = False, max_tracks: int | None = None):
    """Run Discover Weekly sync in the background. Returns a sanitized result dict."""
    settings = get_settings()
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return {"status": "not_authenticated"}

        req = SyncDiscoverWeeklyRequest(dry_run=dry_run, max_tracks=max_tracks)

        cfg, run, added = _run(sync_discover_weekly(db, settings, user, req))
        return {"status": run.status, "run_id": run.id, "tracks_added_count": int(added)}

    except SpotifyApiError as e:
        retries = getattr(self.request, "retries", 0)
        countdown = min(60, 2 ** retries)
        if e.status_code in (429, 500, 502, 503, 504, None) and retries < self.max_retries:
            raise self.retry(countdown=countdown)
        return {"status": "error"}
    except Exception:
        retries = getattr(self.request, "retries", 0)
        countdown = min(60, 2 ** retries)
        if retries < self.max_retries:
            raise self.retry(countdown=countdown)
        return {"status": "error"}
    finally:
        db.close()

