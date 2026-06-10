from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from gateway.config import Settings


class GatewayJwtError(Exception):
    pass


def issue_tenant_token(
    org_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    expire_minutes: int | None = None,
) -> str:
    settings = settings or Settings()
    if not settings.jwt_secret:
        raise GatewayJwtError("GATEWAY_JWT_SECRET not configured")
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(org_id),
        "org_id": str(org_id),
        "exp": now + timedelta(minutes=expire_minutes or settings.jwt_expire_minutes),
        "iat": now,
    }
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_tenant_token(token: str, *, settings: Settings | None = None) -> uuid.UUID:
    settings = settings or Settings()
    if not settings.jwt_secret:
        raise GatewayJwtError("GATEWAY_JWT_SECRET not configured")
    decode_kwargs: dict[str, Any] = {
        "algorithms": [settings.jwt_algorithm],
        "options": {"require": ["exp", "sub", "org_id"]},
    }
    if settings.jwt_audience:
        decode_kwargs["audience"] = settings.jwt_audience
    try:
        payload = jwt.decode(token, settings.jwt_secret, **decode_kwargs)
    except InvalidTokenError as exc:
        raise GatewayJwtError(str(exc)) from exc
    try:
        return uuid.UUID(str(payload["org_id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise GatewayJwtError("Invalid org_id claim") from exc
