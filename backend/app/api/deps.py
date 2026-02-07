"""Shared API dependencies (DB session, rate limit hooks)."""
from fastapi import Request

from app.config import get_settings


def get_settings_dep():
    return get_settings()


async def rate_limit_key(request: Request) -> str:
    """Key for rate limiting; use forwarded IP or client when behind proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
