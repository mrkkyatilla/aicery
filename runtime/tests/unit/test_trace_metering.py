from core.domain.usage import LlmUsage
from runtime.adapters.trace.memory import InMemoryTracePort
from runtime.services.trace_recorder import TraceRecorder


def test_record_llm_persists_usage_metadata():
    port = InMemoryTracePort()
    recorder = TraceRecorder(port)
    usage = LlmUsage(provider="mock", model="mock", tokens_in=10, tokens_out=5)
    recorder.record_llm(
        run_id="run-1",
        name="provider.stream",
        messages=[{"role": "user", "content": "hi"}],
        output="echo:hi",
        model="mock",
        usage=usage,
    )
    steps = port.list_by_run("run-1")
    assert len(steps) == 1
    assert steps[0].metadata["usage"]["tokens_in"] == 10
    assert steps[0].metadata["usage"]["provider"] == "mock"
