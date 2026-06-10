from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Canonical API error_code values (string literals stable for clients)."""

    GRAPH_STEP_LIMIT = "GRAPH_STEP_LIMIT"
    HITL_APPROVAL_REQUIRED = "HITL_APPROVAL_REQUIRED"
    HITL_REJECTED = "HITL_REJECTED"
    HITL_APPROVAL_MISSING = "HITL_APPROVAL_MISSING"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    REPLAY_MISMATCH = "REPLAY_MISMATCH"
    REPLAY_INPUT_MISMATCH = "REPLAY_INPUT_MISMATCH"
    UNKNOWN_AGENT = "UNKNOWN_AGENT"
    AGENT_MANIFEST_ERROR = "AGENT_MANIFEST_ERROR"
    RUN_FAILED = "RUN_FAILED"


HTTP_STATUS_FOR_ERROR: dict[ErrorCode, int] = {
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.QUOTA_EXCEEDED: 402,
    ErrorCode.GRAPH_STEP_LIMIT: 400,
    ErrorCode.HITL_APPROVAL_REQUIRED: 409,
    ErrorCode.INVALID_STATE_TRANSITION: 409,
    ErrorCode.UNKNOWN_AGENT: 404,
    ErrorCode.AGENT_MANIFEST_ERROR: 500,
}


def http_status_for(error_code: ErrorCode | str | None) -> int:
    if error_code is None:
        return 500
    if isinstance(error_code, ErrorCode):
        return HTTP_STATUS_FOR_ERROR.get(error_code, 500)
    try:
        return HTTP_STATUS_FOR_ERROR.get(ErrorCode(error_code), 500)
    except ValueError:
        return 500
