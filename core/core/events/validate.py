from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

from core.events.constants import (
    SUBJECT_AGENT_STEP,
    SUBJECT_RUN_COMPLETED,
    SUBJECT_RUN_FAILED,
    SUBJECT_RUN_STARTED,
    SUBJECT_TOOL_CALLED,
)
from core.events.envelope import EventEnvelope, envelope_to_dict

_SCHEMAS_DIR = Path(__file__).parent / "schemas" / "v1"

_PAYLOAD_BY_SUBJECT = {
    SUBJECT_RUN_STARTED: "run.started.payload.json",
    SUBJECT_RUN_COMPLETED: "run.completed.payload.json",
    SUBJECT_RUN_FAILED: "run.failed.payload.json",
    SUBJECT_AGENT_STEP: "agent.step.payload.json",
    SUBJECT_TOOL_CALLED: "tool.called.payload.json",
}


class EventValidationError(ValueError):
    pass


@lru_cache
def _load_validator(filename: str) -> Draft202012Validator:
    path = _SCHEMAS_DIR / filename
    schema = json.loads(path.read_text())
    return Draft202012Validator(schema)


def validate_envelope(data: dict | EventEnvelope) -> None:
    if isinstance(data, EventEnvelope):
        data = envelope_to_dict(data)

    try:
        _load_validator("envelope.json").validate(data)
    except jsonschema.ValidationError as exc:
        raise EventValidationError(str(exc)) from exc

    payload_schema = _PAYLOAD_BY_SUBJECT.get(data["subject"])
    if payload_schema:
        try:
            _load_validator(payload_schema).validate(data.get("payload", {}))
        except jsonschema.ValidationError as exc:
            raise EventValidationError(str(exc)) from exc
