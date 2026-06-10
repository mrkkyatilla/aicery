import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from agents.manifest import load_manifest
from runtime.adapters.db import session as session_mod
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.adapters.db.models import Base, RunApprovalORM
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.services.hitl_sweeper import sweep_expired_hitl_once


@pytest.fixture
def sweeper_env(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("HITL_ENABLED", "true")
    monkeypatch.setenv("HITL_APPROVAL_TTL_SEC", "1")
    monkeypatch.setenv("HITL_SWEEPER_ENABLED", "false")
    monkeypatch.chdir(tmp_path)

    load_manifest.cache_clear()
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
    load_manifest.cache_clear()


def test_sweeper_fails_expired_suspended_run(sweeper_env) -> None:
    client = sweeper_env
    headers = {"X-API-Key": "dev"}
    created = client.post(
        "/v1/runs",
        json={"agent_id": "hitl-demo", "input": "ttl probe", "execute": True},
        headers=headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    suspended = False
    for _ in range(80):
        body = client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] == "suspended":
            suspended = True
            break
        time.sleep(0.05)
    assert suspended

    factory = session_mod.get_session_factory()
    session = factory()
    pending = ApprovalRepository(session).get_open_for_run(run_id)
    assert pending is not None
    row = session.get(RunApprovalORM, uuid.UUID(pending.approval_id))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(seconds=5)
    session.commit()
    session.close()

    import os

    os.environ["HITL_SWEEPER_ENABLED"] = "true"
    count = sweep_expired_hitl_once(factory)
    assert count >= 1

    final = client.get(f"/v1/runs/{run_id}", headers=headers).json()
    assert final["status"] == "failed"
    assert final["error_code"] == "HITL_REJECTED"
