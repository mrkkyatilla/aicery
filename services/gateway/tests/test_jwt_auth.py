import uuid

import pytest

from gateway.config import Settings
from gateway.services.jwt_auth import GatewayJwtError, decode_tenant_token, issue_tenant_token


def test_issue_and_decode_tenant_jwt(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "gateway-test-secret-32bytes-long!!")
    org_id = uuid.uuid4()
    token = issue_tenant_token(org_id)
    decoded = decode_tenant_token(token)
    assert decoded == org_id


def test_decode_invalid_jwt_raises(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "gateway-test-secret-32bytes-long!!")
    with pytest.raises(GatewayJwtError):
        decode_tenant_token("not-a-jwt")
