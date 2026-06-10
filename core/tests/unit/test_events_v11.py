from core.domain.run import Run
from core.events import SUBJECT_AGENT_STEP, SUBJECT_TOOL_CALLED, build_envelope, validate_envelope


def test_tool_called_envelope_validates() -> None:
    run = Run(
        id="550e8400-e29b-41d4-a716-446655440000",
        agent_id="research",
        input_text="test",
    )
    envelope = build_envelope(
        SUBJECT_TOOL_CALLED,
        run,
        {
            "tool_name": "read_file",
            "arguments_hash": "sha256:deadbeef",
            "duration_ms": 12,
            "success": True,
            "error_code": None,
        },
    )
    validate_envelope(envelope)


def test_agent_step_envelope_validates() -> None:
    run = Run(
        id="550e8400-e29b-41d4-a716-446655440001",
        agent_id="research",
        input_text="test",
    )
    envelope = build_envelope(
        SUBJECT_AGENT_STEP,
        run,
        {"agent_id": "research", "node": "planner", "step_index": 1},
    )
    validate_envelope(envelope)
