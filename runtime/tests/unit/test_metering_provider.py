import pytest

from runtime.adapters.providers.metering import MeteringProvider
from runtime.adapters.providers.mock import MockProvider
from runtime.adapters.providers.openai import OpenAIProvider
from runtime.adapters.providers.usage_helpers import usage_from_openai_response


@pytest.mark.asyncio
async def test_metering_provider_collects_mock_usage():
    wrapped = MeteringProvider(MockProvider(), provider="mock", model="mock")
    text = await wrapped.complete([{"role": "user", "content": "hi"}])
    assert text.startswith("echo:")
    usage = wrapped.pop_usage()
    assert usage is not None
    assert usage.provider == "mock"
    assert usage.tokens_in >= 1
    assert usage.tokens_out >= 1


def test_usage_from_openai_response():
    usage = usage_from_openai_response(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        provider="openai",
        model="gpt-4o-mini",
    )
    assert usage is not None
    assert usage.tokens_in == 10
    assert usage.tokens_out == 5


@pytest.mark.asyncio
async def test_openai_complete_sets_last_usage(monkeypatch):
    provider = OpenAIProvider("sk-test", model="gpt-4o-mini")

    async def fake_post(_path: str, _payload: dict) -> dict:
        return {
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }

    monkeypatch.setattr(provider, "_post_json", fake_post)
    await provider.complete([{"role": "user", "content": "hi"}])
    assert provider.last_usage is not None
    assert provider.last_usage.tokens_in == 3
    assert provider.last_usage.tokens_out == 2
