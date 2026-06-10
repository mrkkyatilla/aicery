import pytest
from fastapi.testclient import TestClient

from core.domain.run import Run, RunStatus
from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.memory.factory import get_hot_memory, reset_hot_memory
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.services.hot_memory_hooks import memory_key_for_run


@pytest.fixture
def conv_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "true")

    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    set_test_publisher(InMemoryEventPublisher())
    app = create_app()
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as client:
        yield client
    set_test_publisher(None)
    reset_event_publisher()
    reset_hot_memory()


def test_create_run_without_conversation_id_defaults_to_run_id(conv_client: TestClient) -> None:
    headers = {"X-API-Key": "dev"}
    response = conv_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hi", "execute": False},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["conversation_id"] == body["id"]


def test_create_run_with_explicit_conversation_id(conv_client: TestClient) -> None:
    headers = {"X-API-Key": "dev"}
    response = conv_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "hi",
            "execute": False,
            "conversation_id": "conv-abc-123",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["conversation_id"] == "conv-abc-123"


def test_memory_key_for_run() -> None:
    run = Run(
        id="run-1",
        agent_id="echo",
        input_text="x",
        conversation_id="conv-shared",
    )
    assert memory_key_for_run(run) == "conv-shared"
    run2 = Run(id="run-2", agent_id="echo", input_text="x")
    assert memory_key_for_run(run2) == "run-2"


@pytest.mark.asyncio
async def test_two_runs_same_conversation_share_hot_memory(monkeypatch) -> None:
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "true")
    reset_hot_memory()
    memory = get_hot_memory()
    assert memory is not None
    conv = "shared-conv-001"
    await memory.append_turn(conv, "user", "first")
    await memory.append_turn(conv, "assistant", "echo:first")

    run2 = Run(
        id="run-second",
        agent_id="echo",
        input_text="second",
        status=RunStatus.RUNNING,
        conversation_id=conv,
    )
    from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
    from runtime.adapters.providers.mock import MockProvider

    class CapturingMockProvider(MockProvider):
        def __init__(self) -> None:
            super().__init__()
            self.last_messages: list[dict] = []

        async def stream(self, messages: list[dict], **kwargs):
            self.last_messages = list(messages)
            async for token in super().stream(messages, **kwargs):
                yield token

    provider = CapturingMockProvider()
    orchestrator = LangGraphOrchestrator(provider=provider)
    async for _ in orchestrator.stream(run2):
        pass
    contents = [m.get("content") for m in provider.last_messages]
    assert "first" in contents
