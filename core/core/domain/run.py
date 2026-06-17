from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from core.domain.provider_policy import ProviderPolicy


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset(
    {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RunCreate(BaseModel):
    agent_id: str = Field(min_length=1)
    input_text: str
    workspace_id: str | None = None
    host_workspace_root: str | None = None
    pipeline_id: str | None = None
    conversation_id: str | None = None
    provider_policy: ProviderPolicy | None = None


class Run(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: RunStatus = RunStatus.PENDING
    agent_id: str = Field(min_length=1)
    input_text: str
    workspace_id: str | None = None
    host_workspace_root: str | None = None
    pipeline_id: str | None = None
    conversation_id: str | None = None
    provider_policy: ProviderPolicy | None = None
    output_text: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    error_code: str | None = None
    error_message: str | None = None
