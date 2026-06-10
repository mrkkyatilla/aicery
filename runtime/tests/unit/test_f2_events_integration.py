import time

import pytest
from fastapi.testclient import TestClient

from core.events import SUBJECT_AGENT_STEP, SUBJECT_TOOL_CALLED
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
def event_client(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("# Aicery runtime\n", encoding="utf-8")

    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
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


def test_research_run_emits_tool_called_and_agent_step(event_client) -> None:
    test_client, publisher = event_client
    headers = {"X-API-Key": "dev"}
    created = test_client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "input": "Summarize README.md",
            "execute": True,
        },
        headers=headers,
    )
    run_id = created.json()["id"]

    for _ in range(60):
        body = test_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)

    subjects = [e["subject"] for e in publisher.published]
    assert SUBJECT_TOOL_CALLED in subjects
    assert SUBJECT_AGENT_STEP in subjects
