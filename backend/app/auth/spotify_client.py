"""Spotify OAuth and API wrapper; token refresh and DB update (no tokens in logs)."""
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import OAuthToken, User

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SCOPES = "playlist-read-private playlist-modify-private playlist-modify-public user-read-private"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SpotifyAuthError(Exception):
    pass


def get_authorize_url(redirect_uri: str, state: str, client_id: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    code: str,
    redirect_uri: str,
    settings: Settings,
) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(settings.client_id, settings.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        raise SpotifyAuthError(f"Token exchange failed: {resp.status_code}")
    return resp.json()


async def refresh_tokens(refresh_token: str, settings: Settings) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(settings.client_id, settings.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        raise SpotifyAuthError(f"Refresh failed: {resp.status_code}")
    return resp.json()


async def get_current_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise SpotifyAuthError(f"Me request failed: {resp.status_code}")
    return resp.json()


def _expires_at(expires_in_seconds: int) -> datetime:
    return _utc_now() + timedelta(seconds=expires_in_seconds)


def upsert_user_and_tokens(
    db: Session,
    spotify_user_id: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    scope: str | None,
) -> User:
    user = db.query(User).filter(User.spotify_user_id == spotify_user_id).first()
    if not user:
        user = User(spotify_user_id=spotify_user_id)
        db.add(user)
        db.flush()
    token_row = db.query(OAuthToken).filter(OAuthToken.user_id == user.id).first()
    expires_at = _expires_at(expires_in)
    if token_row:
        token_row.access_token = access_token
        token_row.refresh_token = refresh_token
        token_row.expires_at = expires_at
        token_row.scope = scope
    else:
        token_row = OAuthToken(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope,
        )
        db.add(token_row)
    db.commit()
    db.refresh(user)
    return user


def get_valid_access_token(db: Session, user_id: int, settings: Settings) -> str | None:
    """Return access token for user; refresh and update DB if expired. Sync for use from sync context."""
    import asyncio
    token_row = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
    if not token_row:
        return None
    buffer_seconds = 60
    if (token_row.expires_at - _utc_now()).total_seconds() > buffer_seconds:
        return token_row.access_token
    try:
        new_data = asyncio.run(refresh_tokens(token_row.refresh_token, settings))
    except SpotifyAuthError:
        return None
    new_access = new_data.get("access_token")
    new_expires_in = new_data.get("expires_in", 3600)
    new_refresh = new_data.get("refresh_token") or token_row.refresh_token
    token_row.access_token = new_access
    token_row.refresh_token = new_refresh
    token_row.expires_at = _expires_at(new_expires_in)
    db.commit()
    return new_access


async def get_valid_access_token_async(
    db: Session, user_id: int, settings: Settings
) -> str | None:
    """Async version for use in request handlers."""
    token_row = db.query(OAuthToken).filter(OAuthToken.user_id == user_id).first()
    if not token_row:
        return None
    buffer_seconds = 60
    if (token_row.expires_at - _utc_now()).total_seconds() > buffer_seconds:
        return token_row.access_token
    try:
        new_data = await refresh_tokens(token_row.refresh_token, settings)
    except SpotifyAuthError:
        return None
    new_access = new_data.get("access_token")
    new_expires_in = new_data.get("expires_in", 3600)
    new_refresh = new_data.get("refresh_token") or token_row.refresh_token
    token_row.access_token = new_access
    token_row.refresh_token = new_refresh
    token_row.expires_at = _expires_at(new_expires_in)
    db.commit()
    return new_access
