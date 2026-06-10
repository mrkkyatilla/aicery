import pytest

from runtime.adapters.memory.factory import get_hot_memory, reset_hot_memory
from runtime.adapters.memory.redis_hot import RedisHotMemory


class _FakeRedis:
    def __init__(self) -> None:
        self._lists: dict[str, list[str]] = {}
        self._ttl: dict[str, int] = {}

    def rpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).append(value)

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self._lists.get(key, [])
        if not items:
            return []
        if end == -1:
            end = len(items) - 1
        return items[start : end + 1]

    def expire(self, key: str, ttl: int) -> None:
        self._ttl[key] = ttl

    def delete(self, key: str) -> None:
        self._lists.pop(key, None)
        self._ttl.pop(key, None)


@pytest.fixture(autouse=True)
def reset_memory():
    reset_hot_memory()
    yield
    reset_hot_memory()


@pytest.mark.asyncio
async def test_redis_hot_memory_append_and_get() -> None:
    fake = _FakeRedis()
    mem = RedisHotMemory(redis_url="redis://fake", ttl_sec=60)
    mem._client = fake  # type: ignore[method-assign]

    await mem.append_turn("conv-1", "user", "hi")
    await mem.append_turn("conv-1", "assistant", "hello")

    turns = await mem.get_recent_turns("conv-1", limit=10)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["content"] == "hello"
    assert fake._ttl["hot:conv-1"] == 60


@pytest.mark.asyncio
async def test_factory_uses_redis_backend(monkeypatch) -> None:
    monkeypatch.setenv("HOT_MEMORY_ENABLED", "true")
    monkeypatch.setenv("HOT_MEMORY_BACKEND", "redis")

    fake = _FakeRedis()

    def _fake_client():
        return fake

    def patched_get_client(self):
        self._client = fake
        return self._client

    monkeypatch.setattr(RedisHotMemory, "_get_client", patched_get_client)

    memory = get_hot_memory()
    assert memory is not None
    await memory.append_turn("k1", "user", "test")
    turns = await memory.get_recent_turns("k1")
    assert turns[0]["content"] == "test"
