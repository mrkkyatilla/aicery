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
def inventory_client(monkeypatch):
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


def _wait_completed(client: TestClient, run_id: str, headers: dict) -> dict:
    terminal = None
    for _ in range(120):
        body = client.get(f"/v1/runs/{run_id}", headers=headers).json()
        terminal = body
        if body["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)
    assert terminal is not None
    return terminal


def test_inventory_advisor_run_completed(inventory_client) -> None:
    headers = {"X-API-Key": "dev"}
    created = inventory_client.post(
        "/v1/runs",
        json={
            "agent_id": "inventory-advisor",
            "input": "SKU-42 stok ve tedarik durumu",
            "execute": True,
        },
        headers=headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    final = _wait_completed(inventory_client, run_id, headers)
    assert final["status"] == "completed", final
    output = final.get("output_text") or ""
    assert "12" in output or "SKU-42" in output
    assert "Alpha Supply" in output or "echo:" in output
