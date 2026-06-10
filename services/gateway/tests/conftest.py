import pytest

from gateway.adapters.db.models import Base
from gateway.adapters.db import session as session_mod
from gateway.adapters.db.repositories import ApiKeyRepository, OrgRepository, WorkspaceRepository
from gateway.adapters.db.session import get_session_factory
from gateway.services.auth import generate_api_key, hash_api_key


@pytest.fixture
def tenant_headers():
    factory = get_session_factory()
    session = factory()
    org = OrgRepository(session).create("proxy-org")
    key = generate_api_key()
    ApiKeyRepository(session).create(
        org_id=org.id,
        key_hash=hash_api_key(key),
        key_prefix=key[:12],
        name="default",
    )
    WorkspaceRepository(session).create(
        org_id=org.id, name="default", runtime_workspace_id="tenant-ws"
    )
    org_id = org.id
    session.close()
    return {"X-Api-Key": key}, org_id


@pytest.fixture(autouse=True)
def gateway_db(monkeypatch):
    monkeypatch.setenv("GATEWAY_DATABASE_URL", "sqlite://")
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    session_mod._engine = None
    session_mod._SessionLocal = None
