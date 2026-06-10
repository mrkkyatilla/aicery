import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.domain.tool import ToolCallRecord
from runtime.adapters.db.models import ToolCallORM


def _to_domain(row: ToolCallORM) -> ToolCallRecord:
    return ToolCallRecord(
        id=str(row.id),
        run_id=str(row.run_id),
        tool_name=row.tool_name,
        arguments=row.arguments,
        result=row.result,
        error_code=row.error_code,
        duration_ms=row.duration_ms,
        created_at=row.created_at,
    )


def _to_orm(record: ToolCallRecord) -> ToolCallORM:
    return ToolCallORM(
        id=uuid.UUID(record.id),
        run_id=uuid.UUID(record.run_id),
        tool_name=record.tool_name,
        arguments=record.arguments,
        result=record.result,
        error_code=record.error_code,
        duration_ms=record.duration_ms,
        created_at=record.created_at,
    )


class ToolCallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, record: ToolCallRecord) -> ToolCallRecord:
        row = _to_orm(record)
        self._session.add(row)
        self._session.flush()
        self._session.commit()
        return _to_domain(row)

    def list_by_run(self, run_id: str) -> list[ToolCallRecord]:
        stmt = select(ToolCallORM).where(ToolCallORM.run_id == uuid.UUID(run_id))
        rows = self._session.scalars(stmt).all()
        return [_to_domain(row) for row in rows]

    def count_by_run(self, run_id: str) -> int:
        stmt = select(func.count()).select_from(ToolCallORM).where(
            ToolCallORM.run_id == uuid.UUID(run_id)
        )
        return int(self._session.scalar(stmt) or 0)
