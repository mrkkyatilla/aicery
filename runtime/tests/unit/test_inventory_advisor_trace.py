import time
from pathlib import Path

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
from runtime.api.rate_limit import reset_rate_limiter

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def inventory_trace_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("WORKSPACE_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("PLUGIN_PATHS", "examples/stock-advisor")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    reset_rate_limiter()
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


def test_inventory_advisor_trace_has_tool_steps(inventory_trace_client) -> None:
    headers = {"X-API-Key": "dev"}
    created = inventory_trace_client.post(
        "/v1/runs",
        json={
            "agent_id": "inventory-advisor",
            "input": "SKU-42 stok analizi",
            "execute": True,
        },
        headers=headers,
    )
    run_id = created.json()["id"]

    for _ in range(120):
        body = inventory_trace_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)

    trace = inventory_trace_client.get(f"/v1/runs/{run_id}/trace", headers=headers).json()
    tool_names = {s["name"] for s in trace["steps"] if s["type"] == "tool"}
    assert "get_stock" in tool_names
    assert "search_suppliers" in tool_names
