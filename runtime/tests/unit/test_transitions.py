import pytest

from core.domain.errors import InvalidStateTransitionError
from core.domain.run import RunCreate, RunStatus
from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.services.run_service import RunService


@pytest.mark.asyncio
async def test_invalid_transition_raises(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = session_mod.get_session_factory()()

    emitter = RunEventEmitter(InMemoryEventPublisher())
    service = RunService(session, LangGraphOrchestrator(MockProvider()), emitter)

    run = await service.create_run(RunCreate(agent_id="echo", input_text="hi"), execute=False)
    run = await service.transition(run, RunStatus.RUNNING)

    with pytest.raises(InvalidStateTransitionError):
        await service.transition(run, RunStatus.PENDING)
