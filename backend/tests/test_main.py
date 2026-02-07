"""Basic API and config tests."""
import pytest
from app.config import get_settings


@pytest.mark.asyncio
async def test_health(client):
    """Health endpoint returns ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_load():
    """Settings load from env with sensible defaults."""
    s = get_settings()
    assert s.app_name
    assert s.rate_limit_requests > 0
    assert isinstance(s.allowed_origins, list)
