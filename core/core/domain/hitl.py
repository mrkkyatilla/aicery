from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class HitlMode(StrEnum):
    GRAPH = "graph"
    EXECUTOR = "executor"


def hitl_mode_from_checkpoint(checkpoint: dict) -> HitlMode:
    raw = checkpoint.get("hitl_mode")
    if raw == HitlMode.EXECUTOR.value:
        return HitlMode.EXECUTOR
    if raw == HitlMode.GRAPH.value:
        return HitlMode.GRAPH
    if checkpoint.get("graph") or checkpoint.get("thread_id"):
        return HitlMode.GRAPH
    return HitlMode.EXECUTOR


class PendingApproval(BaseModel):
    approval_id: str
    run_id: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    checkpoint: dict = Field(default_factory=dict)
    expires_at: datetime
    resolved: bool = False
    decision: ApprovalDecision | None = None
    final_arguments: dict | None = None
    created_at: datetime | None = None
