from typing import Protocol

from core.domain.run import Run
from core.domain.tool import ToolCallRecord


class HotMemoryPort(Protocol):
    """Redis — conversational turns, TTL (F1+)."""

    async def append_turn(self, run_id: str, role: str, content: str) -> None: ...

    async def get_recent_turns(self, run_id: str, limit: int = 20) -> list[dict]: ...

    async def clear(self, run_id: str) -> None: ...

    async def get_compacted_state(self, run_id: str) -> dict | None: ...

    async def set_compacted_state(self, run_id: str, state: dict) -> None: ...

    async def replace_turns_with_compacted(self, run_id: str, state: dict) -> None: ...


class StructuredMemoryPort(Protocol):
    """Postgres — durable audit."""

    async def save_run(self, run: Run) -> None: ...

    async def get_run(self, run_id: str) -> Run | None: ...

    async def append_tool_call(self, record: ToolCallRecord) -> None: ...

    async def list_tool_calls(self, run_id: str) -> list[ToolCallRecord]: ...


class MemoryPort(HotMemoryPort, StructuredMemoryPort, Protocol):
    """Deprecated F0 monolith; prefer split ports."""

    ...
