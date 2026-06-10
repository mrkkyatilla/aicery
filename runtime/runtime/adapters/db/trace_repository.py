import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.domain.trace import TraceStep, TraceStepType
from runtime.adapters.db.models import TraceStepORM


def _to_domain(row: TraceStepORM) -> TraceStep:
    return TraceStep(
        step_id=str(row.step_id),
        run_id=str(row.run_id),
        type=TraceStepType(row.type),
        name=row.name,
        parent_step_id=str(row.parent_step_id) if row.parent_step_id else None,
        input_hash=row.input_hash,
        output_hash=row.output_hash,
        input_preview=row.input_preview,
        output_preview=row.output_preview,
        metadata=row.metadata_json or {},
        status=row.status,  # type: ignore[arg-type]
        error_code=row.error_code,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def _to_orm(step: TraceStep) -> TraceStepORM:
    return TraceStepORM(
        step_id=uuid.UUID(step.step_id),
        run_id=uuid.UUID(step.run_id),
        type=step.type.value,
        name=step.name,
        parent_step_id=uuid.UUID(step.parent_step_id) if step.parent_step_id else None,
        input_hash=step.input_hash,
        output_hash=step.output_hash,
        input_preview=step.input_preview,
        output_preview=step.output_preview,
        metadata_json=step.metadata,
        status=step.status,
        error_code=step.error_code,
        started_at=step.started_at,
        ended_at=step.ended_at,
    )


class TraceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, step: TraceStep) -> None:
        try:
            self._session.add(_to_orm(step))
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def list_by_run(self, run_id: str) -> list[TraceStep]:
        stmt = (
            select(TraceStepORM)
            .where(TraceStepORM.run_id == uuid.UUID(run_id))
            .order_by(TraceStepORM.started_at.asc())
        )
        rows = self._session.scalars(stmt).all()
        return [_to_domain(r) for r in rows]
