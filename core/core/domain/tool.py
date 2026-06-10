from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ToolRef(BaseModel):
    name: str
    input_schema: dict = Field(default_factory=dict)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ToolCallRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    result: dict | None = None
    error_code: str | None = None
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=_utc_now)
