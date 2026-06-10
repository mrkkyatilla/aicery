import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app


@pytest.fixture
def chain_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "false")
    monkeypatch.setenv("MAX_GRAPH_STEPS", "2")

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


def test_research_chain_fails_when_graph_step_limit_exceeded(chain_client: TestClient) -> None:
    headers = {"X-API-Key": "dev"}
    response = chain_client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "pipeline": "research-chain",
            "input": "Summarize workspace",
            "execute": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    run_id = response.json()["id"]

    import time

    terminal = None
    for _ in range(80):
        body = chain_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed", "cancelled"):
            terminal = body
            break
        time.sleep(0.1)

    assert terminal is not None
    assert terminal["status"] == "failed"
    assert terminal.get("error_code") == "GRAPH_STEP_LIMIT"
