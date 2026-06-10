from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class TraceStepType(StrEnum):
    LLM = "llm"
    TOOL = "tool"
    AGENT = "agent"
    SYSTEM = "system"
    HUMAN = "human"


TraceStepStatus = Literal["ok", "error", "skipped"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TraceStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    type: TraceStepType
    name: str
    parent_step_id: str | None = None
    input_hash: str = ""
    output_hash: str | None = None
    input_preview: str | None = None
    output_preview: str | None = None
    metadata: dict = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=_utc_now)
    ended_at: datetime | None = None
    status: TraceStepStatus = "ok"
    error_code: str | None = None
