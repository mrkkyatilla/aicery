from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from core.domain.hitl import ApprovalDecision, HitlMode, PendingApproval, hitl_mode_from_checkpoint
from core.domain.trace import TraceStep, TraceStepType
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.config import Settings
from runtime.services.trace_recorder import TraceRecorder


@dataclass(frozen=True)
class ResumePlan:
    hitl_mode: HitlMode
    resume_payload: dict | None
    spawn_continuation: bool
    signal_event: bool


class HitlCoordinator:
    """Shared HITL pending/resume logic for graph and executor strategies."""

    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        self._repo = ApprovalRepository(session)
        self._settings = settings or Settings()
        self._trace = trace_recorder

    def create_pending(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict,
        hitl_mode: HitlMode,
        checkpoint_extra: dict | None = None,
    ) -> PendingApproval:
        expires_at = datetime.now(UTC) + timedelta(seconds=self._settings.hitl_approval_ttl_sec)
        checkpoint: dict[str, Any] = {"hitl_mode": hitl_mode.value}
        if checkpoint_extra:
            checkpoint.update(checkpoint_extra)
        return self._repo.create_pending(
            run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
            checkpoint=checkpoint,
            expires_at=expires_at,
        )

    def create_graph_pending(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict,
        graph: str,
        interrupt_node: str | None = None,
        checkpoint_id: str | None = None,
    ) -> PendingApproval:
        extra: dict[str, Any] = {
            "thread_id": run_id,
            "graph": graph,
            "interrupt_node": interrupt_node,
        }
        if checkpoint_id:
            extra["checkpoint_id"] = checkpoint_id
        return self.create_pending(
            run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
            hitl_mode=HitlMode.GRAPH,
            checkpoint_extra=extra,
        )

    def create_executor_pending(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict,
        agent_id: str,
    ) -> PendingApproval:
        return self.create_pending(
            run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
            hitl_mode=HitlMode.EXECUTOR,
            checkpoint_extra={"agent_id": agent_id, "tool_name": tool_name},
        )

    @staticmethod
    def build_approval_chunk(
        pending: PendingApproval,
        *,
        interrupt_node: str | None = None,
    ) -> dict:
        mode = hitl_mode_from_checkpoint(pending.checkpoint)
        chunk = {
            "type": "approval_required",
            "status": "awaiting_human_approval",
            "approval_id": pending.approval_id,
            "tool_name": pending.tool_name,
            "arguments": pending.arguments,
            "expires_at": pending.expires_at.astimezone(UTC).isoformat(),
            "hitl_mode": mode.value,
        }
        node = interrupt_node or pending.checkpoint.get("interrupt_node")
        if node:
            chunk["interrupt_node"] = node
        return chunk

    @staticmethod
    def is_graph_mode(pending: PendingApproval) -> bool:
        return hitl_mode_from_checkpoint(pending.checkpoint) == HitlMode.GRAPH

    def build_resume_plan(
        self,
        pending: PendingApproval,
        *,
        decision: ApprovalDecision,
        arguments: dict | None = None,
    ) -> ResumePlan:
        mode = hitl_mode_from_checkpoint(pending.checkpoint)
        if decision == ApprovalDecision.REJECT:
            return ResumePlan(
                hitl_mode=mode,
                resume_payload=None,
                spawn_continuation=False,
                signal_event=False,
            )
        resume_payload: dict[str, Any] = {"decision": decision.value}
        if decision == ApprovalDecision.MODIFY and arguments is not None:
            resume_payload["arguments"] = arguments
        if mode == HitlMode.GRAPH:
            return ResumePlan(
                hitl_mode=mode,
                resume_payload=resume_payload,
                spawn_continuation=True,
                signal_event=False,
            )
        return ResumePlan(
            hitl_mode=mode,
            resume_payload=None,
            spawn_continuation=False,
            signal_event=True,
        )

    def record_graph_interrupt(
        self,
        run_id: str,
        payload: dict,
        approval_id: str,
    ) -> None:
        if self._trace is None:
            return
        self._trace.append(
            TraceStep(
                run_id=run_id,
                type=TraceStepType.SYSTEM,
                name="graph.interrupt",
                input_hash=approval_id,
                metadata={
                    "graph_interrupt": True,
                    "tool_name": payload.get("tool_name"),
                    "interrupt_node": payload.get("node"),
                    "graph": payload.get("graph", "research-chain"),
                },
                status="ok",
                ended_at=datetime.now(UTC),
            )
        )

    async def capture_checkpoint_id(self, graph, config: dict) -> str | None:
        snapshot = await graph.aget_state(config)
        if not snapshot or not snapshot.config:
            return None
        configurable = snapshot.config.get("configurable") or {}
        return configurable.get("checkpoint_id")
