"""DB model tests: metadata and token non-exposure (CWE-532)."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.models import User, OAuthToken, PlaylistConfig, PlaylistRun


@pytest.fixture
def in_memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_oauth_token_repr_does_not_contain_tokens():
    token = OAuthToken(
        id=1,
        user_id=1,
        access_token="secret_access_123",
        refresh_token="secret_refresh_456",
        expires_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
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
