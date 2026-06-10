from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.domain.hitl import ApprovalDecision, PendingApproval
from runtime.adapters.db.models import RunApprovalORM


class ApprovalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_pending(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict,
        checkpoint: dict,
        expires_at: datetime,
    ) -> PendingApproval:
        existing = self.get_open_for_run(run_id)
        if existing is not None:
            return existing

        approval_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        row = RunApprovalORM(
            approval_id=uuid.UUID(approval_id),
            run_id=uuid.UUID(run_id),
            tool_name=tool_name,
            arguments=arguments,
            checkpoint=checkpoint,
            expires_at=expires_at,
            resolved=False,
            created_at=now,
        )
        self._session.add(row)
        self._session.commit()
        return _to_domain(row)

    def get_open_for_run(self, run_id: str) -> PendingApproval | None:
        stmt = (
            select(RunApprovalORM)
            .where(RunApprovalORM.run_id == uuid.UUID(run_id))
            .where(RunApprovalORM.resolved.is_(False))
            .order_by(RunApprovalORM.created_at.desc())
            .limit(1)
        )
        row = self._session.scalars(stmt).first()
        return _to_domain(row) if row else None

    def get_resolved_for_run_tool(
        self, run_id: str, tool_name: str
    ) -> PendingApproval | None:
        stmt = (
            select(RunApprovalORM)
            .where(RunApprovalORM.run_id == uuid.UUID(run_id))
            .where(RunApprovalORM.tool_name == tool_name)
            .where(RunApprovalORM.resolved.is_(True))
            .order_by(RunApprovalORM.resolved_at.desc())
            .limit(1)
        )
        row = self._session.scalars(stmt).first()
        return _to_domain(row) if row else None

    def get_by_id(self, approval_id: str) -> PendingApproval | None:
        row = self._session.get(RunApprovalORM, uuid.UUID(approval_id))
        return _to_domain(row) if row else None

    def list_expired_open(self, now: datetime) -> list[PendingApproval]:
        stmt = (
            select(RunApprovalORM)
            .where(RunApprovalORM.resolved.is_(False))
            .where(RunApprovalORM.expires_at < now)
            .order_by(RunApprovalORM.expires_at.asc())
        )
        rows = self._session.scalars(stmt).all()
        return [_to_domain(row) for row in rows]

    def resolve(
        self,
        approval_id: str,
        *,
        decision: ApprovalDecision,
        final_arguments: dict | None = None,
    ) -> PendingApproval | None:
        row = self._session.get(RunApprovalORM, uuid.UUID(approval_id))
        if row is None or row.resolved:
            return _to_domain(row) if row else None
        row.resolved = True
        row.decision = decision.value
        row.final_arguments = final_arguments
        row.resolved_at = datetime.now(UTC)
        self._session.commit()
        return _to_domain(row)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _to_domain(row: RunApprovalORM) -> PendingApproval:
    decision = ApprovalDecision(row.decision) if row.decision else None
    return PendingApproval(
        approval_id=str(row.approval_id),
        run_id=str(row.run_id),
        tool_name=row.tool_name,
        arguments=dict(row.arguments or {}),
        checkpoint=dict(row.checkpoint or {}),
        expires_at=_ensure_utc(row.expires_at),
        resolved=row.resolved,
        decision=decision,
        final_arguments=row.final_arguments,
        created_at=row.created_at,
    )
