"""OAuth state and session: signed cookies, safe redirects (CWE-352, CWE-601, CWE-614)."""
import hashlib
import hmac
import secrets
from urllib.parse import urlparse

from fastapi import Request, Response


STATE_COOKIE_NAME = "spotify_oauth_state"
STATE_COOKIE_MAX_AGE = 600
SESSION_COOKIE_NAME = "spotify_session"
SESSION_COOKIE_MAX_AGE = 86400 * 7  # 7 days


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def generate_state(secret: str) -> str:
    raw = secrets.token_urlsafe(32)
    return f"{raw}.{_sign(secret, raw)}"


def verify_state(secret: str, cookie_value: str | None, query_state: str | None) -> bool:
    if not cookie_value or not query_state or cookie_value != query_state:
        return False
    parts = cookie_value.split(".", 1)
    if len(parts) != 2:
        return False
    raw, sig = parts[0], parts[1]
    if not raw or not sig:
        return False
    expected = _sign(secret, raw)
    return hmac.compare_digest(expected, sig)


def set_state_cookie(response: Response, state: str, secret: str, secure: bool) -> None:
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        max_age=STATE_COOKIE_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def clear_state_cookie(response: Response) -> None:
    response.delete_cookie(STATE_COOKIE_NAME, httponly=True, samesite="lax")


def build_session_cookie_value(user_id: int, secret: str) -> str:
    raw = str(user_id)
    return f"{raw}.{_sign(secret, raw)}"


def parse_session_cookie(cookies: dict, secret: str) -> int | None:
    val = cookies.get(SESSION_COOKIE_NAME)
    if not val:
        return None
    parts = val.split(".", 1)
    if len(parts) != 2:
        return None
    raw, sig = parts[0], parts[1]
    try:
        uid = int(raw)
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(secret, raw), sig):
        return None
    return uid


def set_session_cookie(response: Response, user_id: int, secret: str, secure: bool) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=build_session_cookie_value(user_id, secret),
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, samesite="lax")


def is_safe_redirect_url(url: str, allowed_origins: list[str]) -> bool:
    """Only allow redirect to same-origin or configured frontend (CWE-601)."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return False
    return origin.rstrip("/") in (o.rstrip("/") for o in allowed_origins)


def get_safe_success_redirect(allowed_origins: list[str], override: str | None) -> str:
    if override:
        if override.startswith(("http://", "https://")) and is_safe_redirect_url(override, allowed_origins):
            return override
        if override.startswith("/") and allowed_origins:
            return allowed_origins[0].rstrip("/") + override
    if allowed_origins:
        return allowed_origins[0].rstrip("/") + "/"
    return "/"
