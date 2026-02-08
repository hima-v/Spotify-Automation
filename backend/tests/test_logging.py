"""Tests for logging redaction (no tokens/secrets in logs)."""
import pytest
from app.core.logging import redact_message


def test_redact_token_param():
    assert "access_token=***" in redact_message("access_token=abc123xyz")
    assert "refresh_token=***" in redact_message("refresh_token=secret")


def test_redact_bearer():
    assert redact_message("Bearer eyJhbGciOiJIUzI1NiJ9.xxx.yyy") == "Bearer ***"


def test_redact_password():
    assert "password=***" in redact_message("password=super_secret")


def test_redact_passthrough_safe():
    assert redact_message("User logged in") == "User logged in"
