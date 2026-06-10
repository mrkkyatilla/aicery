import pytest
from pydantic import ValidationError

from core.domain.run import Run, RunCreate, RunStatus


def test_run_create_requires_agent_id() -> None:
    with pytest.raises(ValidationError):
        RunCreate(agent_id="", input_text="hello")


def test_run_defaults_pending() -> None:
    run = Run(agent_id="echo", input_text="hello")
    assert run.status == RunStatus.PENDING
    assert len(run.id) == 36


def test_run_rejects_empty_agent_id() -> None:
    with pytest.raises(ValidationError):
        Run(agent_id="", input_text="hello")
