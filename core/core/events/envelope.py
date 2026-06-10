from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from core.domain.run import Run
from core.events.constants import SCHEMA_VERSION


class EventEnvelope(BaseModel):
    schema_version: str = SCHEMA_VERSION
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    run_id: str
    workspace_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict = Field(default_factory=dict)


def build_envelope(subject: str, run: Run, payload: dict | None = None) -> EventEnvelope:
    return EventEnvelope(
        subject=subject,
        run_id=run.id,
        workspace_id=run.workspace_id,
        payload=payload or {},
    )


def envelope_to_dict(envelope: EventEnvelope) -> dict:
    data = envelope.model_dump(mode="json")
    data["timestamp"] = envelope.timestamp.isoformat()
    return data
