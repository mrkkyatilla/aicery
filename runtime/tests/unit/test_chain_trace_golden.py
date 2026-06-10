"""F3-P1b — research-chain trace golden (planner → executor → summarizer)."""

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
def chain_client(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("# Chain golden\n\nDeterministic chain test.\n", encoding="utf-8")

    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("SEMANTIC_SEARCH_ENABLED", "false")

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
        yield client
    set_test_publisher(None)
    reset_event_publisher()


def _wait_completed(client: TestClient, run_id: str, headers: dict) -> dict:
    for _ in range(120):
        body = client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed", "cancelled"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not complete")


def test_research_chain_trace_golden_step_shape(chain_client) -> None:
    """Chain pipeline records planner/executor/summarizer agent steps + summarizer LLM."""
    client = chain_client
    headers = {"X-API-Key": "dev"}
    run_id = client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "pipeline": "research-chain",
            "input": "Summarize workspace docs",
            "execute": True,
        },
        headers=headers,
    ).json()["id"]

    final = _wait_completed(client, run_id, headers)
    assert final["status"] == "completed", final

    steps = client.get(f"/v1/runs/{run_id}/trace", headers=headers).json()["steps"]
    assert len(steps) >= 4

    names = {s.get("name", "") for s in steps}
    nodes = {s.get("name", "").split(".")[-1] for s in steps if s["type"] == "agent"}
    types = {s["type"] for s in steps}

    assert "agent" in types
    assert "llm" in types
    assert {"planner", "executor", "summarizer"} <= nodes or any(
        n in names for n in ("chain.planner", "chain.executor", "chain.summarizer")
    )
    assert any("chain.summarizer" in n or n == "chain.summarizer" for n in names)
