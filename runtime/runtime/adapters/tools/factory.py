from agents.manifest import AgentManifestError, get_allowed_tools
from core.domain.replay import ReplayContext, ReplayMode
from core.ports.tool_executor import ToolExecutorPort
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.adapters.tools.approval_executor import ApprovalToolExecutor
from runtime.adapters.tools.mock_executor import MockToolExecutor
from runtime.adapters.tools.persisting_executor import PersistingToolExecutor
from runtime.adapters.tools.tracing_executor import TracingToolExecutor
from runtime.config import Settings
from runtime.services.trace_recorder import TraceRecorder


def build_tool_executor(
    agent_id: str,
    *,
    pipeline_id: str | None = None,
    workspace_root: str | None = None,
    replay_ctx: ReplayContext | None = None,
    trace_recorder: TraceRecorder | None = None,
    trace_session=None,
) -> ToolExecutorPort:
    ctx = replay_ctx or ReplayContext()
    if ctx.is_replay and ctx.mock_tools and ctx.source_run_id:
        if trace_session is None:
            from runtime.adapters.db.session import get_session_factory

            trace_session = get_session_factory()()
            try:
                steps = TraceRepository(trace_session).list_by_run(ctx.source_run_id)
            finally:
                trace_session.close()
        else:
            steps = TraceRepository(trace_session).list_by_run(ctx.source_run_id)
        return MockToolExecutor(steps, trace_recorder=trace_recorder)

    settings = Settings()
    root = workspace_root or settings.workspace_root
    try:
        allowed = get_allowed_tools(agent_id)
    except AgentManifestError:
        allowed = []

    executor: ToolExecutorPort = PersistingToolExecutor(
        workspace_root=root,
        allowed_tools=allowed,
        agent_id=agent_id,
    )
    if trace_recorder is not None:
        executor = TracingToolExecutor(executor, trace_recorder)
    if trace_session is not None and pipeline_id != "research-chain" and agent_id != "hitl-demo":
        executor = ApprovalToolExecutor(
            executor,
            agent_id=agent_id,
            approval_repo=ApprovalRepository(trace_session),
        )
    if settings.chaos_tool_fail_rate > 0 and ctx.mode == ReplayMode.LIVE:
        from runtime.adapters.tools.chaos_executor import ChaosToolExecutor

        executor = ChaosToolExecutor(executor, settings.chaos_tool_fail_rate)
    return executor
