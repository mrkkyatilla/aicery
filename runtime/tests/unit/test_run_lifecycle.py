import time

import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.deps import _get_emitter


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")

    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    publisher = InMemoryEventPublisher()
    set_test_publisher(publisher)
    app = create_app()

    async def override_emitter():
        return RunEventEmitter(publisher)

    app.dependency_overrides[_get_emitter] = override_emitter
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as test_client:
        yield test_client, publisher
    set_test_publisher(None)
    reset_event_publisher()


def test_echo_run_completes(client) -> None:
    test_client, publisher = client
    headers = {"X-API-Key": "dev"}
    response = test_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hello", "execute": True},
        headers=headers,
    )
    assert response.status_code == 201
    run_id = response.json()["id"]

    terminal = None
    for _ in range(60):
        get_resp = test_client.get(f"/v1/runs/{run_id}", headers=headers)
        terminal = get_resp.json()
        if terminal["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert terminal is not None
    assert terminal["status"] == "completed"
    assert "echo:hello" in (terminal.get("output_text") or "")
    subjects = [e["subject"] for e in publisher.published]
    assert "aicery.events.v1.run.started" in subjects
    assert "aicery.events.v1.run.completed" in subjects
