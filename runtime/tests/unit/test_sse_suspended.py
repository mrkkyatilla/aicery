import time

import pytest
from fastapi.testclient import TestClient

from agents.manifest import load_manifest
from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph.checkpointer import reset_checkpointer
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.deps import _get_emitter
from runtime.services.run_execution import get_run_execution


@pytest.fixture
def chain_hitl_client(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("# HITL chain\n\nTest content.\n", encoding="utf-8")

    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "true")
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("SEMANTIC_SEARCH_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    load_manifest.cache_clear()

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
        yield test_client

    set_test_publisher(None)
    reset_event_publisher()
    load_manifest.cache_clear()


@pytest.fixture(autouse=True)
def _reset_checkpointer():
    import asyncio

    asyncio.run(reset_checkpointer())
    yield
    asyncio.run(reset_checkpointer())


def test_sse_suspended_event_on_graph_hitl(chain_hitl_client) -> None:
    headers = {"X-API-Key": "dev"}
    run_id = chain_hitl_client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "pipeline": "research-chain",
            "input": "Summarize README",
            "execute": True,
        },
        headers=headers,
    ).json()["id"]

    events: list[str] = []
    hitl_mode = None
    for _ in range(200):
        state = get_run_execution(run_id)
        if state and state.history:
            for chunk in state.history:
                if chunk.get("type") == "approval_required":
                    hitl_mode = chunk.get("hitl_mode")
                if chunk.get("type") == "suspended":
                    events.append("suspended")
        body = chain_hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] == "suspended":
            if hitl_mode == "graph":
                break
        time.sleep(0.05)

    assert hitl_mode == "graph"
    assert body["status"] == "suspended"
    assert "suspended" in events
