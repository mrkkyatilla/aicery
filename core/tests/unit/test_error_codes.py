from core.domain.error_codes import HTTP_STATUS_FOR_ERROR, ErrorCode, http_status_for


def test_error_code_values_are_unique() -> None:
    values = [member.value for member in ErrorCode]
    assert len(values) == len(set(values))


def test_known_error_codes_snapshot() -> None:
    assert set(ErrorCode) == {
        ErrorCode.GRAPH_STEP_LIMIT,
        ErrorCode.HITL_APPROVAL_REQUIRED,
        ErrorCode.HITL_REJECTED,
        ErrorCode.HITL_APPROVAL_MISSING,
        ErrorCode.RATE_LIMITED,
        ErrorCode.QUOTA_EXCEEDED,
        ErrorCode.INVALID_STATE_TRANSITION,
        ErrorCode.REPLAY_MISMATCH,
        ErrorCode.REPLAY_INPUT_MISMATCH,
        ErrorCode.UNKNOWN_AGENT,
        ErrorCode.AGENT_MANIFEST_ERROR,
        ErrorCode.RUN_FAILED,
    }


def test_http_status_mapping() -> None:
    assert http_status_for(ErrorCode.RATE_LIMITED) == 429
    assert http_status_for(ErrorCode.QUOTA_EXCEEDED) == 402
    assert http_status_for("RATE_LIMITED") == 429
    assert http_status_for("UNKNOWN_CODE") == 500
    assert HTTP_STATUS_FOR_ERROR[ErrorCode.GRAPH_STEP_LIMIT] == 400
