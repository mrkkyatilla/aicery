import time

import pytest
from fastapi.testclient import TestClient

from agents.manifest import load_manifest, tool_requires_approval
from runtime.adapters.db import session as session_mod
from runtime.adapters.db.approval_repository import ApprovalRepository
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
def hitl_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "true")
    monkeypatch.setenv("HITL_APPROVAL_TTL_SEC", "120")

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


def test_manifest_requires_approval_flag() -> None:
    load_manifest.cache_clear()
    assert tool_requires_approval("hitl-demo", "hitl_probe") is True
    assert tool_requires_approval("echo", "read_file") is False


def test_hitl_run_suspends_until_approve(hitl_client) -> None:
    headers = {"X-API-Key": "dev"}
    created = hitl_client.post(
        "/v1/runs",
        json={"agent_id": "hitl-demo", "input": "probe", "execute": True},
        headers=headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    suspended = False
    approval_id = None
    for _ in range(80):
        body = hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] == "suspended":
            suspended = True
            factory = session_mod.get_session_factory()
            session = factory()
            pending = ApprovalRepository(session).get_open_for_run(run_id)
            session.close()
            if pending:
                approval_id = pending.approval_id
            break
        time.sleep(0.05)
    assert suspended, "run should reach suspended"
    assert approval_id

    resumed = hitl_client.post(
        f"/v1/runs/{run_id}/resume",
        json={"decision": "approve", "approval_id": approval_id},
        headers=headers,
    )
    assert resumed.status_code == 200

    for _ in range(80):
        body = hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] == "completed":
            break
        time.sleep(0.05)
    assert hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()["status"] == "completed"

    trace = hitl_client.get(f"/v1/runs/{run_id}/trace", headers=headers).json()
    assert any(s["type"] == "human" for s in trace["steps"])


def test_hitl_reject_fails_run(hitl_client) -> None:
    headers = {"X-API-Key": "dev"}
    created = hitl_client.post(
        "/v1/runs",
        json={"agent_id": "hitl-demo", "input": "reject-me", "execute": True},
        headers=headers,
    )
    run_id = created.json()["id"]

    approval_id = None
    for _ in range(80):
        body = hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] == "suspended":
            factory = session_mod.get_session_factory()
            session = factory()
            pending = ApprovalRepository(session).get_open_for_run(run_id)
            session.close()
            approval_id = pending.approval_id if pending else None
            break
        time.sleep(0.05)
    assert approval_id

    hitl_client.post(
        f"/v1/runs/{run_id}/resume",
        json={"decision": "reject", "approval_id": approval_id},
        headers=headers,
    )

    for _ in range(80):
        body = hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("failed", "cancelled"):
            break
        time.sleep(0.05)
    final = hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
    assert final["status"] == "failed"
    assert final.get("error_code") == "HITL_REJECTED"


def test_hitl_disabled_skips_suspend(hitl_client, monkeypatch) -> None:
    monkeypatch.setenv("HITL_ENABLED", "false")
    headers = {"X-API-Key": "dev"}
    created = hitl_client.post(
        "/v1/runs",
        json={"agent_id": "hitl-demo", "input": "auto", "execute": True},
        headers=headers,
    )
    run_id = created.json()["id"]
    for _ in range(80):
        body = hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    assert hitl_client.get(f"/v1/runs/{run_id}", headers=headers).json()["status"] == "completed"
