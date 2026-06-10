from typing import Protocol

from core.domain.trace import TraceStep


class TracePort(Protocol):
    """Append-only trace store (F3)."""

    def append(self, step: TraceStep) -> None: ...

    def list_by_run(self, run_id: str) -> list[TraceStep]: ...
