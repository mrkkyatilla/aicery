import pytest

from runtime.adapters.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_emits_at_least_100_chunks(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_STREAM_CHUNKS", "100")
    provider = MockProvider()
    chunks: list[str] = []
    async for token in provider.stream([{"role": "user", "content": "hello"}]):
        chunks.append(token)
    assert len(chunks) >= 100
