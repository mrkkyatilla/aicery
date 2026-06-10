"""Live Gemini tests — skip unless GEMINI_API_KEY is set (never commit the key)."""

import os

import pytest

from runtime.adapters.providers.factory import get_provider
from runtime.adapters.providers.gemini import GeminiProvider
from runtime.adapters.providers.mock import MockProvider

pytestmark = pytest.mark.live

pytest.importorskip("google.genai")


def _require_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        pytest.skip("GEMINI_API_KEY not set")
    return key


@pytest.mark.asyncio
async def test_gemini_complete_returns_text() -> None:
    provider = GeminiProvider(api_key=_require_key())
    text = await provider.complete([{"role": "user", "content": "Say hello in one word."}])
    assert text
    assert len(text) > 0
    assert "echo:" not in text.lower()


@pytest.mark.asyncio
async def test_gemini_stream_yields_chunks() -> None:
    provider = GeminiProvider(api_key=_require_key())
    chunks: list[str] = []
    async for token in provider.stream(
        [{"role": "user", "content": "Count from one to five, one number per line."}]
    ):
        chunks.append(token)
    assert chunks
    joined = "".join(chunks)
    assert len(joined) > 3
    assert "echo:" not in joined.lower()


@pytest.mark.asyncio
async def test_factory_uses_gemini_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", _require_key())
    monkeypatch.setenv("USE_MOCK_PROVIDER", "false")
    provider = get_provider()
    assert isinstance(provider, GeminiProvider)


def test_factory_uses_mock_without_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    provider = get_provider()
    assert isinstance(provider, MockProvider)
