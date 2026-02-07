"""Strict input schemas (CWE-20). Extend as endpoints are added."""
from pydantic import BaseModel, Field


class HealthQuery(BaseModel):
    """Example schema; replace with real payloads when implementing."""

    echo: str | None = Field(default=None, max_length=100)
