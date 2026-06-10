import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.api.app import create_app
from runtime.config import Settings
from runtime.intelligence.indexer import IndexResult
from runtime.services.index_job_service import IndexJobStatus


@pytest.fixture
def index_job_client(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("SEMANTIC_SEARCH_ENABLED", "true")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_index_async_returns_202(index_job_client, monkeypatch):
    client = index_job_client
    settings = Settings()
    job_id = str(uuid.uuid4())
    service = MagicMock()
    service.enqueue_index.return_value = job_id
    service.get_job = AsyncMock(
        return_value=IndexJobStatus(
            job_id=job_id,
            status="completed",
            workspace_id="local",
            paths=["guide/"],
            result=IndexResult(
                workspace_id="local",
                files_indexed=1,
                chunks_upserted=2,
                duration_ms=10,
            ),
        )
    )
    monkeypatch.setattr("runtime.api.routes.workspace.get_index_job_service", lambda: service)

    response = client.post(
        "/v1/workspace/index?async=true",
        headers={"X-API-Key": settings.api_key},
        json={"workspace_id": "local", "paths": ["guide/"]},
    )
    assert response.status_code == 202
    assert response.json()["job_id"] == job_id

    status_resp = client.get(
        f"/v1/workspace/index/jobs/{job_id}",
        headers={"X-API-Key": settings.api_key},
    )
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "completed"
    assert body["result"]["files_indexed"] == 1
