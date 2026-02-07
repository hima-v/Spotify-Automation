"""Pytest fixtures. Set required env before importing app (fail-fast config)."""
import os
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/spotify_playlist_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("SPOTIFY_CLIENT_ID", "test_client_id")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("APP_SECRET", "a" * 32)
os.environ.setdefault("BASE_URL", "http://localhost:8000")

from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
