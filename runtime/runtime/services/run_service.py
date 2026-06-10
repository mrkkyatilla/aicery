from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.domain.hitl import ApprovalDecision
from core.domain.replay import ReplayContext
from core.domain.run import Run, RunCreate, RunStatus
from core.domain.transitions import assert_transition
from core.events import (
    SUBJECT_AGENT_STEP,
    SUBJECT_RUN_COMPLETED,
    SUBJECT_RUN_FAILED,
    SUBJECT_RUN_STARTED,
)
from core.ports.orchestrator import OrchestratorPort
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.adapters.db.repository import RunRepository
from runtime.adapters.db.session import get_session_factory
from runtime.adapters.db.tool_call_repository import ToolCallRepository
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.adapters.events.counters import get_event_count
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.orchestrator_factory import build_orchestrator
from runtime.api.replay import validate_replay_input
from runtime.config import Settings
from runtime.observability.run_context import run_otel_context
from runtime.services.hitl_coordinator import HitlCoordinator
from runtime.services.hitl_service import HitlService
from runtime.services.hot_memory_hooks import persist_run_turns
from runtime.services.run_execution import (
    get_run_execution,
    register_run,
    remove_run,
    request_cancel,
)
from runtime.services.trace_recorder import TraceRecorder
from runtime.services.usage_service import (
    build_run_completed_usage_payload,
    export_run_usage,
    summarize_run_usage,
)

logger = logging.getLogger(__name__)


class RunService:
    def __init__(
        self,
        session: Session,
        orchestrator: OrchestratorPort,
        emitter: RunEventEmitter,
        settings: Settings | None = None,
        replay_ctx: ReplayContext | None = None,
    ) -> None:
        self._session = session
        self._repo = RunRepository(session)
        self._orchestrator = orchestrator
        self._emitter = emitter
        self._settings = settings or Settings()
        self._replay_ctx = replay_ctx or ReplayContext()

    async def create_run(self, data: RunCreate, *, execute: bool = False) -> Run:
        if self._replay_ctx.is_replay:
            validate_replay_input(self._replay_ctx.source_run_id or "", data.input_text)
        run = self._repo.create(data)
        if execute:
            state = register_run(run.id)
            state.task = asyncio.create_task(self._execute_run(run.id))
        return run

    async def get_run(self, run_id: str) -> Run | None:
        return self._repo.get(run_id)

    async def get_run_metrics(self, run_id: str) -> tuple[Run | None, int, int]:
        run = self._repo.get(run_id)
        if run is None:
            return None, 0, 0
        tool_calls = ToolCallRepository(self._session).count_by_run(run_id)
        events = get_event_count(run_id)
        return run, tool_calls, events

    async def transition(self, run: Run, target: RunStatus) -> Run:
        assert_transition(run.status, target)
        run.status = target
        run.updated_at = datetime.now(UTC)
        return self._repo.update(run)

    async def cancel_run(self, run_id: str) -> Run | None:
        request_cancel(run_id)
        run = self._repo.get(run_id)
        if run is None:
            return None
        if run.status in (RunStatus.PENDING, RunStatus.RUNNING, RunStatus.SUSPENDED):
            run.status = RunStatus.CANCELLED
            run.updated_at = datetime.now(UTC)
            return self._repo.update(run)
        return run

    async def resume_run(
        self,
        run_id: str,
        *,
        decision: ApprovalDecision,
        approval_id: str | None = None,
        arguments: dict | None = None,
    ) -> Run | None:
        run = self._repo.get(run_id)
        if run is None:
            return None
        if run.status != RunStatus.SUSPENDED:
            raise ValueError(f"Run {run_id} is not suspended")

        repo = ApprovalRepository(self._session)
        pending = repo.get_by_id(approval_id) if approval_id else repo.get_open_for_run(run_id)
        if pending is None:
            raise ValueError("No pending approval for run")

        trace_recorder = TraceRecorder(TraceRepository(self._session))
        hitl = HitlService(self._session, settings=self._settings, trace_recorder=trace_recorder)
        coordinator = HitlCoordinator(self._session, settings=self._settings, trace_recorder=trace_recorder)
        hitl.resolve(pending.approval_id, decision=decision, arguments=arguments)
        if decision == ApprovalDecision.REJECT:
            run.status = RunStatus.FAILED
            run.error_code = "HITL_REJECTED"
            run.error_message = "Human rejected tool execution"
            run.updated_at = datetime.now(UTC)
            return self._repo.update(run)

        run = await self.transition(run, RunStatus.RUNNING)
        plan = coordinator.build_resume_plan(pending, decision=decision, arguments=arguments)
        state = get_run_execution(run_id)

        if plan.spawn_continuation:
            if state is None:
                state = register_run(run_id)
            if state.task is None or state.task.done():
                state.task = asyncio.create_task(
                    self._execute_run_continuation(run_id, plan.resume_payload or {})
                )
            return run

        if plan.signal_event:
            if state is not None:
                state.approval_event.set()
            else:
                raise ValueError("No active run task for executor HITL resume")
            return run

        return run

    async def _execute_run(self, run_id: str) -> None:
        await self._execute_run_inner(run_id, chain_resume=None)

    async def _execute_run_continuation(self, run_id: str, chain_resume: dict) -> None:
        await self._execute_run_inner(run_id, chain_resume=chain_resume)

    async def _execute_run_inner(
        self, run_id: str, *, chain_resume: dict | None
    ) -> None:
        factory = get_session_factory()
        session = factory()
        try:
            trace_recorder = TraceRecorder(TraceRepository(session))
            run_row = RunRepository(session).get(run_id)
            orchestrator = build_orchestrator(
                self._replay_ctx,
                session=session,
                trace_recorder=trace_recorder,
                provider_policy=run_row.provider_policy if run_row else None,
                agent_id=run_row.agent_id if run_row else None,
                chain_resume=chain_resume,
            )
            service = RunService(
                session,
                orchestrator,
                self._emitter,
                self._settings,
                replay_ctx=self._replay_ctx,
            )
            await service._run_lifecycle(run_id, trace_recorder=trace_recorder)
        finally:
            session.close()

    async def _run_lifecycle(
        self,
        run_id: str,
        *,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        state = get_run_execution(run_id)
        run = self._repo.get(run_id)
        if run is None:
            return

        started_at = datetime.now(UTC)
        output_parts: list[str] = []
        final_status = RunStatus.COMPLETED
        error_code: str | None = None
        error_message: str | None = None

        with run_otel_context(run) as otel_ctx:
            if trace_recorder is not None and otel_ctx is not None:
                trace_recorder.set_run_context(otel_ctx)
            try:
                await self._run_lifecycle_body(
                    run_id,
                    state,
                    run,
                    started_at,
                    output_parts,
                    final_status,
                    error_code,
                    error_message,
                    trace_recorder=trace_recorder,
                )
            finally:
                if otel_ctx is not None:
                    latest = self._repo.get(run_id)
                    if latest:
                        otel_ctx.run.status = latest.status
                        otel_ctx.run.error_code = latest.error_code
                if trace_recorder is not None:
                    trace_recorder.set_run_context(None)

    async def _run_lifecycle_body(
        self,
        run_id: str,
        state,
        run: Run,
        started_at: datetime,
        output_parts: list[str],
        final_status: RunStatus,
        error_code: str | None,
        error_message: str | None,
        *,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        try:
            if run.status != RunStatus.RUNNING:
                run = await self.transition(run, RunStatus.RUNNING)
            await self._emitter.emit(
                SUBJECT_RUN_STARTED,
                run,
                {"agent_id": run.agent_id, "input_preview": run.input_text[:200]},
            )

            hitl = HitlService(
                self._session,
                settings=self._settings,
                trace_recorder=trace_recorder,
            )
            restart_stream = True
            while restart_stream:
                restart_stream = False
                async for chunk in self._orchestrator.stream(run):
                    if state and state.cancelled:
                        final_status = RunStatus.CANCELLED
                        break
                    if state:
                        state.history.append(chunk)
                        await state.queue.put(chunk)
                    if chunk.get("type") == "token":
                        output_parts.append(chunk.get("text", ""))
                    elif chunk.get("type") == "step":
                        await self._emitter.emit(
                            SUBJECT_AGENT_STEP,
                            run,
                            {
                                "agent_id": run.agent_id,
                                "node": chunk.get("node", ""),
                                "step_index": chunk.get("index", 0),
                            },
                        )
                    elif chunk.get("type") == "approval_required":
                        pending = ApprovalRepository(self._session).get_by_id(
                            chunk["approval_id"]
                        )
                        if pending is None:
                            final_status = RunStatus.FAILED
                            error_code = "HITL_APPROVAL_MISSING"
                            error_message = "Pending approval not found"
                            break
                        run = await self.transition(run, RunStatus.SUSPENDED)
                        if HitlCoordinator.is_graph_mode(pending):
                            suspended_chunk = {
                                "type": "suspended",
                                "status": "suspended",
                                "run_id": run.id,
                                "approval_id": pending.approval_id,
                            }
                            if state:
                                state.history.append(suspended_chunk)
                                await state.queue.put(suspended_chunk)
                            break
                        if state:
                            state.approval_event.clear()
                        remaining = max(
                            0.0,
                            (pending.expires_at - datetime.now(UTC)).total_seconds(),
                        )
                        decision = await hitl.wait_for_decision(
                            run.id,
                            approval_id=pending.approval_id,
                            timeout_sec=remaining,
                        )
                        if decision is None:
                            decision = hitl.apply_timeout_policy(run, pending)
                        if decision == ApprovalDecision.REJECT:
                            final_status = RunStatus.FAILED
                            error_code = "HITL_REJECTED"
                            error_message = "Human rejected or approval timed out"
                            break
                        run = await self.transition(run, RunStatus.RUNNING)
                        restart_stream = True
                        break
                    elif chunk.get("type") == "error":
                        final_status = RunStatus.FAILED
                        error_code = chunk.get("error_code", "RUN_FAILED")
                        error_message = chunk.get("message", "Run failed")
                        break
                else:
                    continue
                break

            run = self._repo.get(run_id) or run
            if run.status == RunStatus.SUSPENDED:
                return

            run.output_text = "".join(output_parts).strip() or run.output_text
            run.status = final_status
            run.error_code = error_code
            run.error_message = error_message
            run.updated_at = datetime.now(UTC)
            run = self._repo.update(run)

            if run.status == RunStatus.COMPLETED:
                await persist_run_turns(run)
                duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
                tool_calls_count = ToolCallRepository(self._session).count_by_run(run.id)
                trace_steps = TraceRepository(self._session).list_by_run(run.id)
                usage_summary = summarize_run_usage(run.id, trace_steps)
                completed_payload = {
                    "duration_ms": duration_ms,
                    "tool_calls_count": tool_calls_count,
                    "output_preview": (run.output_text or "")[:200],
                    **build_run_completed_usage_payload(usage_summary),
                }
                logger.info(
                    "run.completed",
                    extra={
                        "run_id": run.id,
                        "team": "E2",
                        "duration_ms": duration_ms,
                        "tool_calls_count": tool_calls_count,
                        "tokens_in": usage_summary.tokens_in,
                        "tokens_out": usage_summary.tokens_out,
                    },
                )
                await export_run_usage(run, usage_summary)
                await self._emitter.emit(
                    SUBJECT_RUN_COMPLETED,
                    run,
                    completed_payload,
                )
            elif run.status == RunStatus.FAILED:
                await self._emitter.emit(
                    SUBJECT_RUN_FAILED,
                    run,
                    {
                        "error_code": run.error_code or "RUN_FAILED",
                        "error_message": run.error_message or "Run failed",
                    },
                )
            elif run.status == RunStatus.CANCELLED:
                run = self._repo.update(run)
        except asyncio.CancelledError:
            run = self._repo.get(run_id)
            if run and run.status == RunStatus.RUNNING:
                run.status = RunStatus.CANCELLED
                run.updated_at = datetime.now(UTC)
                self._repo.update(run)
        except Exception as exc:
            logger.exception("Run %s failed", run_id)
            self._session.rollback()
            run = self._repo.get(run_id)
            if run and run.status == RunStatus.RUNNING:
                run.status = RunStatus.FAILED
                run.error_code = getattr(exc, "error_code", "RUN_FAILED")
                run.error_message = str(exc)
                run.updated_at = datetime.now(UTC)
                run = self._repo.update(run)
                await self._emitter.emit(
                    SUBJECT_RUN_FAILED,
                    run,
                    {
                        "error_code": run.error_code,
                        "error_message": run.error_message,
                    },
                )
        finally:
            run = self._repo.get(run_id)
            if state:
                if run and run.status == RunStatus.SUSPENDED:
                    return
                await state.queue.put(
                    {
                        "type": "done",
                        "status": (run.status.value if run else "failed"),
                        "run_id": run_id,
                    }
                )
                remove_run(run_id)
