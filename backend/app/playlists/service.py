from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterable

import httpx
from sqlalchemy.orm import Session

from app.auth.spotify_client import SpotifyAuthError, get_valid_access_token_async
from app.core.config import Settings
from app.db.models import PlaylistConfig, PlaylistRun, User
from app.schemas.playlists import SyncDiscoverWeeklyRequest

logger = logging.getLogger(__name__)

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
DISCOVER_WEEKLY_NAME = "Discover Weekly"
SAVED_WEEKLY_NAME = "Saved Weekly"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SpotifyApiError(Exception):
    def __init__(self, status_code: int | None, message: str):
        super().__init__(message)
        self.status_code = status_code


class SpotifyApi:
    def __init__(self, access_token: str, client: httpx.AsyncClient):
        self._access_token = access_token
        self._client = client

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        max_attempts: int = 4,
    ) -> httpx.Response:
        url = path if path.startswith("http") else f"{SPOTIFY_API_BASE}{path}"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        for attempt in range(1, max_attempts + 1):
            try:
                resp = await self._client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt == max_attempts:
                    raise SpotifyApiError(None, "Spotify request failed") from e
                await asyncio.sleep(self._backoff_seconds(attempt))
                continue

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "1") or "1")
                await asyncio.sleep(min(10, max(1, retry_after)))
                continue

            if resp.status_code in (500, 502, 503, 504):
                if attempt == max_attempts:
                    raise SpotifyApiError(resp.status_code, "Spotify server error")
                await asyncio.sleep(self._backoff_seconds(attempt))
                continue

            return resp

        raise SpotifyApiError(None, "Spotify request failed")

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        base = min(8.0, 0.5 * (2 ** (attempt - 1)))
        return base + random.random() * 0.2

    async def iter_my_playlists(self) -> AsyncIterator[dict[str, Any]]:
        limit = 50
        offset = 0
        max_pages = 3000

        for _ in range(max_pages):
            resp = await self.request("GET", "/me/playlists", params={"limit": limit, "offset": offset})
            if resp.status_code != 200:
                raise SpotifyApiError(resp.status_code, "Failed to list playlists")
            data = resp.json()
            items = data.get("items") or []
            for p in items:
                yield p
            if not data.get("next"):
                return
            offset += limit
        raise SpotifyApiError(None, "Paging guard tripped for playlists")

    async def create_playlist(self, name: str) -> dict[str, Any]:
        resp = await self.request("POST", "/me/playlists", json={"name": name, "public": False})
        if resp.status_code not in (200, 201):
            raise SpotifyApiError(resp.status_code, "Failed to create playlist")
        return resp.json()

    async def iter_playlist_track_items(self, playlist_id: str) -> AsyncIterator[dict[str, Any]]:
        limit = 50
        offset = 0
        max_pages = 5000
        fields = "items(track(id,uri,is_local)),next,offset,limit,total"

        for _ in range(max_pages):
            resp = await self.request(
                "GET",
                f"/playlists/{playlist_id}/tracks",
                params={"limit": limit, "offset": offset, "fields": fields},
            )
            if resp.status_code != 200:
                raise SpotifyApiError(resp.status_code, "Failed to list playlist items")
            data = resp.json()
            items = data.get("items") or []
            for it in items:
                yield it
            if not data.get("next"):
                return
            offset += limit
        raise SpotifyApiError(None, "Paging guard tripped for playlist items")

    async def add_tracks(self, playlist_id: str, uris: list[str]) -> None:
        for chunk in _chunks(uris, 100):
            resp = await self.request("POST", f"/playlists/{playlist_id}/tracks", json={"uris": chunk})
            if resp.status_code not in (200, 201):
                raise SpotifyApiError(resp.status_code, "Failed to add tracks")


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _truncate_error(msg: str, limit: int = 800) -> str:
    msg = msg.strip()
    return msg if len(msg) <= limit else msg[: limit - 3] + "..."


def _get_or_create_discover_weekly_config(db: Session, user_id: int) -> PlaylistConfig:
    cfg = (
        db.query(PlaylistConfig)
        .filter(PlaylistConfig.user_id == user_id)
        .filter(PlaylistConfig.strategy_json == {"kind": "discover_weekly"})
        .first()
    )
    if cfg:
        return cfg
    cfg = PlaylistConfig(
        user_id=user_id,
        source_playlist_id="",
        target_playlist_id="",
        strategy_json={"kind": "discover_weekly"},
        is_enabled=True,
    )
    db.add(cfg)
    db.flush()
    return cfg


def _start_run(db: Session, playlist_config_id: int) -> PlaylistRun:
    run = PlaylistRun(playlist_config_id=playlist_config_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _finish_run_success(db: Session, run: PlaylistRun, tracks_added: int) -> PlaylistRun:
    run.status = "success"
    run.tracks_added_count = tracks_added
    run.finished_at = _utc_now()
    run.error_message = None
    db.commit()
    db.refresh(run)
    return run


def _finish_run_error(db: Session, run: PlaylistRun, message: str, status: str = "error") -> PlaylistRun:
    run.status = status
    run.finished_at = _utc_now()
    run.error_message = _truncate_error(message)
    db.commit()
    db.refresh(run)
    return run


async def sync_discover_weekly(
    db: Session,
    settings: Settings,
    user: User,
    req: SyncDiscoverWeeklyRequest,
) -> tuple[PlaylistConfig, PlaylistRun, int]:
    cfg = _get_or_create_discover_weekly_config(db, user.id)
    run = _start_run(db, cfg.id)

    access_token = await get_valid_access_token_async(db, user.id, settings)
    if not access_token:
        _finish_run_error(db, run, "Not authenticated with Spotify", status="unauthorized")
        raise SpotifyAuthError("Missing token")

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        api = SpotifyApi(access_token, client)

        try:
            discover_id = None
            saved_id = None
            async for p in api.iter_my_playlists():
                name = (p.get("name") or "").strip()
                pid = p.get("id")
                if not pid:
                    continue
                if name == DISCOVER_WEEKLY_NAME:
                    discover_id = pid
                elif name == SAVED_WEEKLY_NAME:
                    saved_id = pid
                if discover_id and saved_id:
                    break

            if not discover_id:
                _finish_run_error(db, run, "Discover Weekly playlist not found", status="not_found")
                raise SpotifyApiError(404, "Discover Weekly not found")

            if not saved_id:
                created = await api.create_playlist(SAVED_WEEKLY_NAME)
                saved_id = created.get("id")
                if not saved_id:
                    raise SpotifyApiError(None, "Created playlist missing id")

            cfg.source_playlist_id = discover_id
            cfg.target_playlist_id = saved_id
            db.commit()

            existing_target_ids: set[str] = set()
            async for item in api.iter_playlist_track_items(saved_id):
                track = item.get("track") or {}
                tid = track.get("id")
                if tid:
                    existing_target_ids.add(tid)

            to_add_uris: list[str] = []
            seen_ids: set[str] = set()
            added_cap = req.max_tracks or 10_000

            async for item in api.iter_playlist_track_items(discover_id):
                track = item.get("track") or {}
                if track.get("is_local") is True:
                    continue
                tid = track.get("id")
                uri = track.get("uri")
                if not tid or not uri:
                    continue
                if tid in existing_target_ids or tid in seen_ids:
                    continue
                seen_ids.add(tid)
                to_add_uris.append(uri)
                if len(to_add_uris) >= added_cap:
                    break

            if not req.dry_run and to_add_uris:
                await api.add_tracks(saved_id, to_add_uris)

            _finish_run_success(db, run, tracks_added=len(to_add_uris))
            return cfg, run, len(to_add_uris)

        except SpotifyApiError as e:
            _finish_run_error(db, run, str(e))
            raise

