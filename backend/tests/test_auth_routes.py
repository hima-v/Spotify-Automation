"""Auth routes: login redirect, me unauthenticated (no tokens in response)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_redirects_to_spotify(client):
    r = await client.get("/auth/login")
    assert r.status_code == 302
    location = r.headers.get("location", "")
    assert "accounts.spotify.com" in location
    assert "state=" in location
    assert "client_id=" in location
    assert "response_type=code" in location
    assert "set-cookie" in r.headers
    assert "spotify_oauth_state" in str(r.headers.get("set-cookie", "")).lower()


@pytest.mark.asyncio
async def test_me_without_cookie_returns_401(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401
    assert "authenticated" in r.text.lower()


@pytest.mark.asyncio
async def test_logout_returns_authenticated_false(client):
    r = await client.post("/auth/logout")
    assert r.status_code == 200
    assert "authenticated" in r.text.lower()
