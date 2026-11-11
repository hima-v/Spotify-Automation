"""DB model tests: metadata and token non-exposure (CWE-532)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import OAuthToken
from app.db.session import Base


@pytest.fixture
def in_memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_oauth_token_repr_does_not_contain_tokens():
    token = OAuthToken(
        id=1,
        user_id=1,
        access_token="secret_access_123",
        refresh_token="secret_refresh_456",
        expires_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        scope="user-read-private",
    )
    r = repr(token)
    assert "secret_access" not in r
    assert "secret_refresh" not in r
    assert "access_token" not in r.lower() or "***" in r
    assert "user_id" in r and "expires_at" in r


def test_metadata_has_all_tables():
    names = {t.name for t in Base.metadata.sorted_tables}
    assert names >= {"users", "oauth_tokens", "playlist_configs", "playlist_runs"}
