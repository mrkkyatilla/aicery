import pytest

from core.domain.run import Run
from core.events import (
    SUBJECT_RUN_STARTED,
    build_envelope,
    validate_envelope,
)
from core.events.validate import EventValidationError


def test_run_started_envelope_validates() -> None:
    run = Run(agent_id="echo", input_text="hello world")
    envelope = build_envelope(
        SUBJECT_RUN_STARTED,
        run,
        {"agent_id": "echo", "input_preview": "hello"},
    )
    validate_envelope(envelope)


def test_invalid_envelope_missing_schema_version() -> None:
    with pytest.raises(EventValidationError):
        validate_envelope(
            {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "subject": SUBJECT_RUN_STARTED,
                "run_id": "550e8400-e29b-41d4-a716-446655440001",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "payload": {"agent_id": "echo"},
            }
        )


def test_transition_rules() -> None:
    from core.domain.run import RunStatus
    from core.domain.transitions import assert_transition

    assert_transition(RunStatus.PENDING, RunStatus.RUNNING)
    from core.domain.errors import InvalidStateTransitionError

    with pytest.raises(InvalidStateTransitionError):
        assert_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
