from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from core.ports.orchestrator import OrchestratorPort
from runtime.adapters.db.session import get_db
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import get_event_publisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.factory import get_provider
from runtime.api.replay import parse_replay_context
from runtime.config import Settings
from runtime.services.run_service import RunService

_orchestrator: OrchestratorPort | None = None
_emitter: RunEventEmitter | None = None


def get_settings() -> Settings:
    return Settings()


async def _get_emitter() -> RunEventEmitter:
    global _emitter
    if _emitter is None:
        publisher = await get_event_publisher()
        _emitter = RunEventEmitter(publisher)
    return _emitter


def get_orchestrator() -> OrchestratorPort:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LangGraphOrchestrator(provider=get_provider())
    return _orchestrator


async def get_run_service(
    session: Annotated[Session, Depends(get_db)],
    emitter: Annotated[RunEventEmitter, Depends(_get_emitter)],
    request: Request,
) -> RunService:
    replay_ctx = parse_replay_context(request)
    return RunService(
        session,
        get_orchestrator(),
        emitter,
        Settings(),
        replay_ctx=replay_ctx,
    )


SettingsDep = Annotated[Settings, Depends(get_settings)]
RunServiceDep = Annotated[RunService, Depends(get_run_service)]
