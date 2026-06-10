from __future__ import annotations

from sqlalchemy.orm import Session

from core.domain.provider_policy import ModelRef, ProviderPolicy
from core.domain.replay import ReplayContext
from core.ports.orchestrator import OrchestratorPort
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.factory import get_provider
from runtime.adapters.providers.replay import TraceReplayProvider
from runtime.config import Settings
from runtime.services.trace_recorder import TraceRecorder


def build_orchestrator(
    replay_ctx: ReplayContext,
    *,
    session: Session | None = None,
    trace_recorder: TraceRecorder | None = None,
    provider_policy: ProviderPolicy | None = None,
    agent_id: str | None = None,
    chain_resume: dict | None = None,
) -> OrchestratorPort:
    settings = Settings()
    llm_ref = ModelRef(provider="gemini", model=settings.gemini_model)
    if replay_ctx.is_replay:
        if session is None:
            from runtime.adapters.db.session import get_session_factory

            session = get_session_factory()()
            steps = TraceRepository(session).list_by_run(replay_ctx.source_run_id or "")
            session.close()
        else:
            steps = TraceRepository(session).list_by_run(replay_ctx.source_run_id or "")
        provider = TraceReplayProvider(steps, model=settings.gemini_model)
    else:
        from runtime.services.policy_resolver import resolve_provider_policy

        resolved = resolve_provider_policy(request_policy=provider_policy, agent_id=agent_id)
        provider = get_provider(policy=provider_policy, agent_id=agent_id)
        llm_ref = resolved.llm
    return LangGraphOrchestrator(
        provider=provider,
        llm_ref=llm_ref,
        replay_ctx=replay_ctx,
        trace_recorder=trace_recorder,
        trace_session=session,
        chain_resume=chain_resume,
    )
