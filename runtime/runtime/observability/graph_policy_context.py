from __future__ import annotations

import contextvars

from runtime.config import Settings

_max_graph_steps: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "aicery_max_graph_steps", default=None
)


def set_max_graph_steps(limit: int | None) -> contextvars.Token[int | None]:
    return _max_graph_steps.set(limit)


def get_max_graph_steps() -> int:
    override = _max_graph_steps.get()
    if override is not None:
        return override
    return Settings().max_graph_steps


def reset_max_graph_steps(token: contextvars.Token[int | None]) -> None:
    _max_graph_steps.reset(token)
