import pytest

from runtime.adapters.providers.failing import FailingProvider
from runtime.adapters.providers.mock import MockProvider
from runtime.adapters.providers.router import ProviderRouter


@pytest.mark.asyncio
async def test_failover_complete_uses_fallback() -> None:
    router = ProviderRouter(FailingProvider(), MockProvider())
    out = await router.complete([{"role": "user", "content": "hi"}])
    assert out == "echo:hi"


@pytest.mark.asyncio
async def test_failover_stream_uses_fallback() -> None:
    router = ProviderRouter(FailingProvider(), MockProvider())
    parts = []
    async for token in router.stream([{"role": "user", "content": "x"}]):
        parts.append(token)
    assert "".join(parts).startswith("echo:x")
