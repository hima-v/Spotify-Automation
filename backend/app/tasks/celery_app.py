"""Celery app (Redis). Chosen over Cloud Tasks for local dev: no GCP dependency, same docker-compose; can add task abstraction later for Cloud Tasks."""
from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "spotify_playlist_manager",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.tasks"],
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
