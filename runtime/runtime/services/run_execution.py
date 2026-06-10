"""In-process run execution tracking for SSE and cancel (F2)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class RunExecutionState:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    history: list[dict] = field(default_factory=list)
    task: asyncio.Task | None = None
    cancelled: bool = False
    approval_event: asyncio.Event = field(default_factory=asyncio.Event)


_registry: dict[str, RunExecutionState] = {}


def register_run(run_id: str) -> RunExecutionState:
    state = RunExecutionState()
    _registry[run_id] = state
    return state


def get_run_execution(run_id: str) -> RunExecutionState | None:
    return _registry.get(run_id)


def remove_run(run_id: str) -> None:
    _registry.pop(run_id, None)


def request_cancel(run_id: str) -> bool:
    state = _registry.get(run_id)
    if state is None:
        return False
    state.cancelled = True
    if state.task and not state.task.done():
        state.task.cancel()
    return True
