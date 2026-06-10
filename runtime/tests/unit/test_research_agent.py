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
def research_client(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("# Aicery\n\nComposable AI runtime.", encoding="utf-8")

    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "false")

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

    with TestClient(app) as client:
        yield client, publisher, tmp_path
    set_test_publisher(None)
    reset_event_publisher()


def test_research_reads_readme(research_client) -> None:
    client, publisher, tmp_path = research_client
    headers = {"X-API-Key": "dev"}
    response = client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "input": "Read README.md and summarize",
            "execute": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    run_id = response.json()["id"]

    terminal = None
    for _ in range(120):
        get_resp = client.get(f"/v1/runs/{run_id}", headers=headers)
        terminal = get_resp.json()
        if terminal["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)

    assert terminal is not None, "run did not reach terminal state"
    assert terminal["status"] == "completed", terminal
    assert "echo:" in (terminal.get("output_text") or "") or "Aicery" in (
        terminal.get("output_text") or ""
    )

    completed = next(
        e for e in publisher.published if e["subject"] == "aicery.events.v1.run.completed"
    )
    assert completed["payload"]["tool_calls_count"] >= 1
