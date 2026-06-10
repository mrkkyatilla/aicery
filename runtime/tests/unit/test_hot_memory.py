import pytest

from runtime.adapters.memory.factory import get_hot_memory, reset_hot_memory
from runtime.adapters.memory.in_memory_hot import InMemoryHotMemory


@pytest.fixture(autouse=True)
def reset_memory():
    reset_hot_memory()
    yield
    reset_hot_memory()


@pytest.mark.asyncio
async def test_append_and_get_recent() -> None:
    mem = InMemoryHotMemory()
    await mem.append_turn("r1", "user", "hi")
    await mem.append_turn("r1", "assistant", "hello")
    turns = await mem.get_recent_turns("r1", limit=10)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["content"] == "hello"


@pytest.mark.asyncio
async def test_factory_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "false")
    assert get_hot_memory() is None


@pytest.mark.asyncio
async def test_factory_enabled_returns_singleton(monkeypatch) -> None:
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "true")
    first = get_hot_memory()
    second = get_hot_memory()
    assert first is not None
    assert first is second
