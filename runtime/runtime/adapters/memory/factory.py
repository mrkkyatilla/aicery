from __future__ import annotations

from core.ports.memory import HotMemoryPort
from runtime.adapters.memory.in_memory_hot import InMemoryHotMemory
from runtime.adapters.memory.redis_hot import RedisHotMemory
from runtime.config import Settings

_memory_instance: HotMemoryPort | None = None


def get_hot_memory() -> HotMemoryPort | None:
    settings = Settings()
    if not settings.hot_memory_enabled:
        return None
    global _memory_instance
    if _memory_instance is None:
        if settings.hot_memory_backend == "redis":
            _memory_instance = RedisHotMemory()
        else:
            _memory_instance = InMemoryHotMemory()
    return _memory_instance


def reset_hot_memory() -> None:
    global _memory_instance
    _memory_instance = None
