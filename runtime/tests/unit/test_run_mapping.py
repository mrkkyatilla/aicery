from datetime import UTC, datetime

from core.domain.run import Run, RunStatus
from runtime.adapters.db.models import RunORM
from runtime.adapters.db.repository import _to_domain, _to_orm


def test_run_domain_orm_roundtrip() -> None:
    run = Run(
        id="550e8400-e29b-41d4-a716-446655440000",
        status=RunStatus.PENDING,
        agent_id="echo",
        input_text="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    row = _to_orm(run)
    back = _to_domain(row)
    assert back.id == run.id
    assert back.status == run.status
    assert back.agent_id == run.agent_id
    assert isinstance(row, RunORM)
