import pytest

from core.domain.run import Run, RunStatus
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.memory.factory import get_hot_memory, reset_hot_memory
from runtime.adapters.providers.mock import MockProvider


class CapturingMockProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__()
        self.last_messages: list[dict] = []

    async def stream(self, messages: list[dict], **kwargs):
        self.last_messages = list(messages)
        async for token in super().stream(messages, **kwargs):
            yield token


@pytest.fixture(autouse=True)
def reset_memory():
    reset_hot_memory()
    yield
    reset_hot_memory()


@pytest.mark.asyncio
async def test_echo_includes_prior_turn_in_context(monkeypatch) -> None:
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "true")
    conv_id = "550e8400-e29b-41d4-a716-446655440099"
    memory = get_hot_memory()
    assert memory is not None
    await memory.append_turn(conv_id, "user", "hello")
    await memory.append_turn(conv_id, "assistant", "echo:hello")

    provider = CapturingMockProvider()
    orchestrator = LangGraphOrchestrator(provider=provider)
    run = Run(
        id="run-follow-up",
        agent_id="echo",
        input_text="second",
        status=RunStatus.RUNNING,
        conversation_id=conv_id,
    )
    async for _chunk in orchestrator.stream(run):
        pass

    contents = [m.get("content") for m in provider.last_messages]
    assert "hello" in contents
    assert "second" in contents
