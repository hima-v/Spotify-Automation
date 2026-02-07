"""Background tasks. Add playlist sync etc. when OAuth is in place."""
from app.tasks.celery_app import celery_app


@celery_app.task
def ping_task() -> str:
    return "pong"
