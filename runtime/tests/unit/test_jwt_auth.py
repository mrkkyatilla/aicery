from datetime import UTC, datetime, timedelta

import jwt
import pytest

from runtime.api.jwt_auth import decode_token, issue_token
from runtime.config import Settings


@pytest.fixture
def jwt_settings() -> Settings:
    return Settings(
        jwt_enabled=True,
        jwt_secret="unit-test-secret",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
    )


def test_issue_and_decode_valid(jwt_settings: Settings) -> None:
    token = issue_token("user-1", workspace_id="ws-1", settings=jwt_settings)
    claims = decode_token(token, settings=jwt_settings)
    assert claims["sub"] == "user-1"
    assert claims["workspace_id"] == "ws-1"


def test_decode_expired_raises(jwt_settings: Settings) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    payload = {"sub": "u", "exp": past, "iat": past}
    token = jwt.encode(payload, jwt_settings.jwt_secret, algorithm=jwt_settings.jwt_algorithm)
    with pytest.raises(ValueError):
        decode_token(token, settings=jwt_settings)


def test_decode_bad_signature_raises(jwt_settings: Settings) -> None:
    token = issue_token("user-1", settings=jwt_settings)
    bad = token[:-4] + "xxxx"
    with pytest.raises(ValueError):
        decode_token(bad, settings=jwt_settings)
