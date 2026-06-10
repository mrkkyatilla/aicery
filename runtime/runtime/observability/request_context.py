from __future__ import annotations

import contextvars

_org_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("aicery_org_id", default=None)


def set_org_id(org_id: str | None) -> contextvars.Token[str | None]:
    return _org_id.set(org_id)


def get_org_id() -> str | None:
    return _org_id.get()


def reset_org_id(token: contextvars.Token[str | None]) -> None:
    _org_id.reset(token)
