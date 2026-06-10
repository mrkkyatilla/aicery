from core.domain.run import Run, RunStatus
from core.ports.orchestrator import OrchestratorPort


class FakeOrchestrator:
    async def execute(self, run: Run) -> Run:
        return run.model_copy(update={"status": RunStatus.COMPLETED})

    async def stream(self, run: Run):
        yield {"type": "done"}
        return

    async def cancel(self, run_id: str) -> None:
        return None


def test_fake_orchestrator_satisfies_port() -> None:
    orch: OrchestratorPort = FakeOrchestrator()
    assert orch is not None
