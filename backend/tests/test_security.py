"""Security helpers: state verification, safe redirect (CWE-601, CWE-352)."""
import pytest
from fastapi import Request, Response

from app.core.security import (
    build_session_cookie_value,
    generate_state,
    get_safe_success_redirect,
    is_safe_redirect_url,
    parse_session_cookie,
    verify_state,
)

SECRET = "test_secret_key_32_bytes_long!!"


def test_generate_state_format():
    s = generate_state(SECRET)
    parts = s.split(".")
    assert len(parts) == 2
    assert len(parts[0]) > 10
    assert len(parts[1]) == 64


def test_verify_state_valid():
    state = generate_state(SECRET)
    assert verify_state(SECRET, state, state) is True


def test_verify_state_tampered_query():
    state = generate_state(SECRET)
    assert verify_state(SECRET, state, state + "x") is False
    assert verify_state(SECRET, state, "other") is False


def test_verify_state_tampered_cookie():
    state = generate_state(SECRET)
    parts = state.split(".")
    bad_cookie = parts[0] + ".wrong_sig"
    assert verify_state(SECRET, bad_cookie, bad_cookie) is False


def test_verify_state_wrong_secret():
    state = generate_state(SECRET)
    assert verify_state("other_secret", state, state) is False


def test_is_safe_redirect_allowed():
    assert is_safe_redirect_url("http://localhost:3000/", ["http://localhost:3000"]) is True
    assert is_safe_redirect_url("https://app.example.com/dash", ["https://app.example.com"]) is True


def test_is_safe_redirect_rejected():
    assert is_safe_redirect_url("https://evil.com/", ["http://localhost:3000"]) is False
    assert is_safe_redirect_url("http://localhost:3000@evil.com/", ["http://localhost:3000"]) is False


def test_get_safe_success_redirect_default():
    url = get_safe_success_redirect(["http://localhost:3000"], None)
    assert url == "http://localhost:3000/"


def test_get_safe_success_redirect_override_path():
    url = get_safe_success_redirect(["http://localhost:3000"], "/dashboard")
    assert url == "http://localhost:3000/dashboard"


def test_session_cookie_roundtrip():
    val = build_session_cookie_value(42, SECRET)
    assert "." in val
    cookies = {"spotify_session": val}
    assert parse_session_cookie(cookies, SECRET) == 42


def test_parse_session_cookie_invalid_signature():
    val = build_session_cookie_value(42, SECRET)
    cookies = {"spotify_session": val}
    assert parse_session_cookie(cookies, "wrong_secret") is None
