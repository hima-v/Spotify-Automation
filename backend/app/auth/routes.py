"""OAuth routes: login, callback, me, logout. No tokens in responses (CWE-532, CWE-601)."""
import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    STATE_COOKIE_NAME,
    clear_session_cookie,
    clear_state_cookie,
    generate_state,
    get_safe_success_redirect,
    parse_session_cookie,
    set_session_cookie,
    set_state_cookie,
    verify_state,
)
from app.db.session import get_db
from app.db.models import User
from app.auth.spotify_client import (
    SpotifyAuthError,
    exchange_code,
    get_authorize_url,
    get_current_user,
    upsert_user_and_tokens,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _callback_uri(settings) -> str:
    base = settings.base_url.rstrip("/")
    return f"{base}/auth/callback"


@router.get("/login")
def login(request: Request):
    settings = get_settings()
    state = generate_state(settings.app_secret)
    redirect_uri = _callback_uri(settings)
    url = get_authorize_url(redirect_uri, state, settings.client_id)
    resp = RedirectResponse(url=url, status_code=302)
    set_state_cookie(resp, state, settings.app_secret, secure=settings.environment == "production")
    return resp


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if error:
        logger.warning("OAuth callback error param: %s", error)
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        resp = RedirectResponse(url=redirect_url, status_code=302)
        clear_state_cookie(resp)
        return resp
    if not code or not state:
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        resp = RedirectResponse(url=redirect_url, status_code=302)
        clear_state_cookie(resp)
        return resp
    cookie_state = request.cookies.get(STATE_COOKIE_NAME)
    if not verify_state(settings.app_secret, cookie_state, state):
        logger.warning("OAuth state mismatch")
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        resp = RedirectResponse(url=redirect_url, status_code=302)
        clear_state_cookie(resp)
        return resp
    redirect_uri = _callback_uri(settings)
    try:
        token_data = await exchange_code(code, redirect_uri, settings)
    except SpotifyAuthError:
        logger.warning("Token exchange failed")
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        return RedirectResponse(url=redirect_url, status_code=302)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    scope = token_data.get("scope")
    if not access_token or not refresh_token:
        logger.warning("Token response missing access or refresh token")
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        return RedirectResponse(url=redirect_url, status_code=302)
    try:
        me = await get_current_user(access_token)
    except SpotifyAuthError:
        logger.warning("Failed to fetch current user")
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        return RedirectResponse(url=redirect_url, status_code=302)
    spotify_user_id = me.get("id")
    if not spotify_user_id:
        logger.warning("Me response missing id")
        redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
        return RedirectResponse(url=redirect_url, status_code=302)
    user = upsert_user_and_tokens(db, spotify_user_id, access_token, refresh_token, expires_in, scope)
    redirect_url = get_safe_success_redirect(settings.allowed_origins, settings.auth_success_redirect)
    resp = RedirectResponse(url=redirect_url, status_code=302)
    clear_state_cookie(resp)
    set_session_cookie(resp, user.id, settings.app_secret, secure=settings.environment == "production")
    return resp


@router.get("/me")
def me(
    request: Request,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    user_id = parse_session_cookie(request.cookies, settings.app_secret)
    if not user_id:
        return Response(content='{"authenticated":false}', status_code=401, media_type="application/json")
    user = db.get(User, user_id)
    if not user:
        return Response(content='{"authenticated":false}', status_code=401, media_type="application/json")
    return {"authenticated": True, "spotify_user_id": user.spotify_user_id}


@router.post("/logout")
def logout():
    resp = Response(content='{"authenticated":false}', media_type="application/json")
    clear_session_cookie(resp)
    return resp
