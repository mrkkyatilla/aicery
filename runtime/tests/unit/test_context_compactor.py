
import pytest

from runtime.adapters.memory.factory import reset_hot_memory
from runtime.adapters.memory.in_memory_hot import InMemoryHotMemory
from runtime.config import Settings
from runtime.services.hot_memory_hooks import (
    build_messages_with_history_async,
    maybe_compact_history,
)


@pytest.fixture(autouse=True)
def _enable_hot_memory(monkeypatch):
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "true")
    monkeypatch.setenv("HOT_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("CONTEXT_COMPACTOR_ENABLED", "true")
    monkeypatch.setenv("COMPACTOR_TURN_THRESHOLD", "5")
    monkeypatch.setenv("COMPACTOR_CHAR_THRESHOLD", "200")
    reset_hot_memory()
    yield
    reset_hot_memory()


@pytest.mark.asyncio
async def test_compact_reduces_turn_count(monkeypatch):
    monkeypatch.setattr("runtime.adapters.memory.factory._memory_instance", InMemoryHotMemory())
    memory = InMemoryHotMemory()
    monkeypatch.setattr("runtime.services.hot_memory_hooks.get_hot_memory", lambda: memory)

    key = "conv-1"
    for i in range(8):
        await memory.append_turn(key, "user", f"Question {i}: " + ("detail " * 20))
        await memory.append_turn(key, "assistant", f"Answer {i}: " + ("response " * 20))

    before = await memory.get_recent_turns(key, limit=50)
    assert len(before) >= 5

    compacted = await maybe_compact_history(key)
    assert compacted is True

    after = await memory.get_recent_turns(key, limit=50)
    assert len(after) == 1
    assert "[compacted]" in after[0]["content"]
    state = await memory.get_compacted_state(key)
    assert state is not None
    assert "summary" in state
    assert state.get("key_facts")


@pytest.mark.asyncio
async def test_build_messages_uses_compacted_history(monkeypatch):
    memory = InMemoryHotMemory()
    monkeypatch.setattr("runtime.services.hot_memory_hooks.get_hot_memory", lambda: memory)
    key = "conv-2"
    for i in range(10):
        await memory.append_turn(key, "user", "x" * 80)
        await memory.append_turn(key, "assistant", "y" * 80)

    messages = await build_messages_with_history_async(
        key,
        system="sys",
        user_content="latest",
    )
    history_chars = sum(len(m["content"]) for m in messages if m["role"] != "system")
    assert history_chars < 8000
    assert messages[-1]["content"] == "latest"


def test_compactor_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CONTEXT_COMPACTOR_ENABLED", raising=False)
    settings = Settings()
    assert settings.context_compactor_enabled is False
