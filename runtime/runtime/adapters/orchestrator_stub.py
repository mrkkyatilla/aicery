from collections.abc import AsyncIterator

from core.domain.run import Run
from core.ports.orchestrator import OrchestratorPort


class StubOrchestrator:
    """F0 placeholder until LangGraph adapter (E3 F1)."""

    async def execute(self, run: Run) -> Run:
        return run

    async def stream(self, run: Run) -> AsyncIterator[dict]:
        yield {"type": "noop"}
        return

    async def cancel(self, run_id: str) -> None:
        return None


def get_stub_orchestrator() -> OrchestratorPort:
    return StubOrchestrator()
