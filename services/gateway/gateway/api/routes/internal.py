from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway.api.deps import SessionDep, require_internal
from gateway.services.billing import ingest_usage_payload

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_internal)],
)


class UsageWebhookPayload(BaseModel):
    run_id: str
    workspace_id: str | None = None
    agent_id: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    llm_calls: int = 0
    lines: list[dict[str, Any]] | None = None


@router.post("/usage")
def receive_usage(body: UsageWebhookPayload, session: SessionDep) -> dict:
    org_id = ingest_usage_payload(session, body.model_dump())
    return {"accepted": True, "org_id": str(org_id) if org_id else None}
