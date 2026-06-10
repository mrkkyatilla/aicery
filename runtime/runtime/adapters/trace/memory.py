from core.domain.trace import TraceStep


class InMemoryTracePort:
    def __init__(self) -> None:
        self._steps: list[TraceStep] = []

    def append(self, step: TraceStep) -> None:
        self._steps.append(step)

    def list_by_run(self, run_id: str) -> list[TraceStep]:
        return [s for s in self._steps if s.run_id == run_id]
