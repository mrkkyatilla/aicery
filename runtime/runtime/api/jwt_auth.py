from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from runtime.config import Settings


def issue_token(
    subject: str,
    *,
    workspace_id: str | None = None,
    settings: Settings | None = None,
) -> str:
    settings = settings or Settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": now,
    }
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    options: dict[str, Any] = {"require": ["exp", "sub"]}
    decode_kwargs: dict[str, Any] = {
        "algorithms": [settings.jwt_algorithm],
        "options": options,
    }
    if settings.jwt_audience:
        decode_kwargs["audience"] = settings.jwt_audience
    try:
        return jwt.decode(token, settings.jwt_secret, **decode_kwargs)
    except InvalidTokenError as exc:
        raise ValueError(str(exc)) from exc
