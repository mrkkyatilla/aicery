from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.domain.hitl import ApprovalDecision, PendingApproval
from core.domain.run import Run
from core.domain.trace import TraceStepType
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.config import Settings
from runtime.services.run_execution import get_run_execution
from runtime.services.trace_recorder import TraceRecorder

logger = logging.getLogger(__name__)


def approval_required_chunk(pending: PendingApproval) -> dict:
    return {
        "type": "approval_required",
        "status": "awaiting_human_approval",
        "approval_id": pending.approval_id,
        "tool_name": pending.tool_name,
        "arguments": pending.arguments,
        "expires_at": pending.expires_at.astimezone(UTC).isoformat(),
    }


class HitlService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        self._session = session
        self._repo = ApprovalRepository(session)
        self._settings = settings or Settings()
        self._trace = trace_recorder

    def get_open_approval(self, run_id: str) -> PendingApproval | None:
        pending = self._repo.get_open_for_run(run_id)
        if pending is None:
            return None
        expires = pending.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= datetime.now(UTC):
            return None
        return pending

    def record_human_action(
        self,
        *,
        run_id: str,
        decision: ApprovalDecision,
        tool_name: str,
        approval_id: str,
        modified_arguments: dict | None = None,
    ) -> None:
        if self._trace is None:
            return
        metadata = {
            "human_action": True,
            "approval_id": approval_id,
            "decision": decision.value,
            "tool_name": tool_name,
        }
        if modified_arguments is not None:
            metadata["modified_arguments"] = modified_arguments
        from core.domain.trace import TraceStep

        self._trace.append(
            TraceStep(
                run_id=run_id,
                type=TraceStepType.HUMAN,
                name=f"human.{decision.value}",
                input_hash=approval_id,
                metadata=metadata,
                status="ok" if decision != ApprovalDecision.REJECT else "error",
                ended_at=datetime.now(UTC),
            )
        )

    async def wait_for_decision(
        self,
        run_id: str,
        *,
        approval_id: str,
        timeout_sec: float,
    ) -> ApprovalDecision | None:
        state = get_run_execution(run_id)
        if state is None:
            return None
        try:
            await asyncio.wait_for(state.approval_event.wait(), timeout=timeout_sec)
        except TimeoutError:
            return None
        pending = self._repo.get_by_id(approval_id)
        if pending is None or not pending.resolved or pending.decision is None:
            return None
        return pending.decision

    def resolve(
        self,
        approval_id: str,
        *,
        decision: ApprovalDecision,
        arguments: dict | None = None,
    ) -> PendingApproval | None:
        final_args = arguments if decision == ApprovalDecision.MODIFY else None
        resolved = self._repo.resolve(
            approval_id,
            decision=decision,
            final_arguments=final_args,
        )
        if resolved is None:
            return None
        self.record_human_action(
            run_id=resolved.run_id,
            decision=decision,
            tool_name=resolved.tool_name,
            approval_id=approval_id,
            modified_arguments=final_args,
        )
        state = get_run_execution(resolved.run_id)
        if state is not None:
            state.approval_event.set()
        return resolved

    def apply_timeout_policy(self, run: Run, pending: PendingApproval) -> ApprovalDecision:
        action = self._settings.hitl_timeout_action.lower()
        if action == "approve":
            decision = ApprovalDecision.APPROVE
        else:
            decision = ApprovalDecision.REJECT
        self.resolve(pending.approval_id, decision=decision)
        logger.info(
            "hitl.timeout",
            extra={"run_id": run.id, "approval_id": pending.approval_id, "decision": decision.value},
        )
        return decision
