from collections.abc import AsyncIterator
from typing import Protocol

from core.domain.run import Run


class OrchestratorPort(Protocol):
    async def execute(self, run: Run) -> Run: ...

    async def stream(self, run: Run) -> AsyncIterator[dict]: ...

    async def cancel(self, run_id: str) -> None: ...
