from __future__ import annotations

import hashlib
import json
import logging

from core.domain.run import Run
from core.events import SUBJECT_TOOL_CALLED, build_envelope, validate_envelope
from core.events.envelope import envelope_to_dict
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import get_event_publisher

logger = logging.getLogger(__name__)


def arguments_hash(arguments: dict) -> str:
    raw = json.dumps(arguments, sort_keys=True, default=str).encode()
    return f"sha256:{hashlib.sha256(raw).hexdigest()[:32]}"


async def emit_tool_called(
    *,
    run_id: str,
    agent_id: str,
    tool_name: str,
    arguments: dict,
    duration_ms: int,
    success: bool,
    error_code: str | None = None,
    workspace_id: str | None = None,
) -> None:
    run = Run(id=run_id, agent_id=agent_id, input_text="", workspace_id=workspace_id)
    payload = {
        "tool_name": tool_name,
        "arguments_hash": arguments_hash(arguments),
        "duration_ms": duration_ms,
        "success": success,
        "error_code": error_code,
    }
    try:
        publisher = await get_event_publisher()
        emitter = RunEventEmitter(publisher)
        await emitter.emit(SUBJECT_TOOL_CALLED, run, payload)
    except Exception:
        logger.exception(
            "Failed to emit tool.called",
            extra={"run_id": run_id, "tool_name": tool_name, "team": "E4"},
        )


def build_tool_called_envelope(**kwargs) -> dict:
    """Sync helper for unit tests."""
    run = Run(id=kwargs["run_id"], agent_id=kwargs["agent_id"], input_text="")
    envelope = build_envelope(
        SUBJECT_TOOL_CALLED,
        run,
        {
            "tool_name": kwargs["tool_name"],
            "arguments_hash": arguments_hash(kwargs["arguments"]),
            "duration_ms": kwargs["duration_ms"],
            "success": kwargs["success"],
            "error_code": kwargs.get("error_code"),
        },
    )
    data = envelope_to_dict(envelope)
    validate_envelope(data)
    return data
