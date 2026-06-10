import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from gateway.adapters.db.models import UsageEventORM
from gateway.adapters.db.repositories import OrgRepository
from gateway.adapters.db.session import get_session_factory
from gateway.api.app import create_app
from gateway.domain.tiers import TIER_LIMITS
from gateway.services.quota import QuotaExceededError, check_run_quota


def test_quota_exceeded_when_at_limit():
    factory = get_session_factory()
    session = factory()
    try:
        org = OrgRepository(session).create("q-org")
        limit = TIER_LIMITS["free"]["agent_run"]
        for i in range(int(limit)):
            session.add(
                UsageEventORM(
                    org_id=org.id,
                    workspace_id="ws",
                    run_id=f"run-{i}",
                    metric="agent_run",
                    quantity=1,
                    unit="count",
                    recorded_at=datetime.now(UTC),
                )
            )
        session.commit()
        with pytest.raises(QuotaExceededError):
            check_run_quota(session, org.id)
    finally:
        session.close()


def test_proxy_returns_402_when_quota_exceeded(monkeypatch):
    factory = get_session_factory()
    session = factory()
    org = OrgRepository(session).create("blocked")
    org_id = org.id
    session.close()

    factory2 = get_session_factory()
    session2 = factory2()
    limit = TIER_LIMITS["free"]["agent_run"]
    for i in range(int(limit)):
        session2.add(
            UsageEventORM(
                org_id=org_id,
                workspace_id="ws",
                run_id=f"r-{i}",
                metric="agent_run",
                quantity=1,
                unit="count",
                recorded_at=datetime.now(UTC),
            )
        )
    session2.commit()
    session2.close()

    from gateway.adapters.db.repositories import ApiKeyRepository, WorkspaceRepository
    from gateway.services.auth import generate_api_key, hash_api_key

    factory3 = get_session_factory()
    session3 = factory3()
    key = generate_api_key()
    ApiKeyRepository(session3).create(
        org_id=org_id,
        key_hash=hash_api_key(key),
        key_prefix=key[:12],
        name="default",
    )
    WorkspaceRepository(session3).create(
        org_id=org_id, name="default", runtime_workspace_id="ws1"
    )
    session3.close()

    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hi", "execute": False},
        headers={"X-Api-Key": key},
    )
    assert response.status_code == 402
    assert response.json()["error_code"] == "QUOTA_EXCEEDED"
