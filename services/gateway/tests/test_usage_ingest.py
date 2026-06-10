import uuid
from datetime import UTC, datetime

from gateway.adapters.db.repositories import OrgRepository, UsageRepository, WorkspaceRepository
from gateway.adapters.db.session import get_session_factory
from gateway.services.billing import ingest_usage_payload
from fastapi.testclient import TestClient
from gateway.api.app import create_app


def test_ingest_usage_idempotent():
    factory = get_session_factory()
    session = factory()
    try:
        org = OrgRepository(session).create("usage-org")
        WorkspaceRepository(session).create(
            org_id=org.id, name="ws", runtime_workspace_id="runtime-ws-1"
        )
        payload = {
            "run_id": "run-abc",
            "workspace_id": "runtime-ws-1",
            "tokens_in": 10,
            "tokens_out": 5,
        }
        org_id = ingest_usage_payload(session, payload)
        assert org_id == org.id
        ingest_usage_payload(session, payload)
        usage = UsageRepository(session)
        assert usage.sum_month(org.id, "agent_run") == 1
        assert usage.sum_month(org.id, "llm_tokens_out") == 5
    finally:
        session.close()


def test_internal_usage_endpoint():
    factory = get_session_factory()
    session = factory()
    org = OrgRepository(session).create("hook-org")
    WorkspaceRepository(session).create(
        org_id=org.id, name="ws", runtime_workspace_id="rw"
    )
    session.commit()
    session.close()

    client = TestClient(create_app())
    response = client.post(
        "/internal/usage",
        json={"run_id": "run-1", "workspace_id": "rw", "tokens_in": 3, "tokens_out": 7},
        headers={"X-Internal-Secret": "internal-dev"},
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True
