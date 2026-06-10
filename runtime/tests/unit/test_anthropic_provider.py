import pytest

from runtime.adapters.providers.anthropic import AnthropicProvider


@pytest.mark.asyncio
async def test_anthropic_complete_uses_api_response(monkeypatch):
    provider = AnthropicProvider("sk-ant-test", model="claude-3-5-haiku-20241022")

    async def fake_post(_path: str, payload: dict) -> dict:
        assert payload["model"] == "claude-3-5-haiku-20241022"
        assert payload["messages"] == [{"role": "user", "content": "hi"}]
        return {
            "content": [{"type": "text", "text": "Hello from Claude"}],
            "usage": {"input_tokens": 4, "output_tokens": 6},
        }

    monkeypatch.setattr(provider, "_post_json", fake_post)
    text = await provider.complete([{"role": "user", "content": "hi"}])
    assert text == "Hello from Claude"
    assert provider.last_usage is not None
    assert provider.last_usage.provider == "anthropic"
    assert provider.last_usage.tokens_in == 4
    assert provider.last_usage.tokens_out == 6


@pytest.mark.asyncio
async def test_anthropic_complete_splits_system_message(monkeypatch):
    provider = AnthropicProvider("sk-ant-test")

    async def fake_post(_path: str, payload: dict) -> dict:
        assert payload["system"] == "Be concise"
        return {"content": [{"text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}}

    monkeypatch.setattr(provider, "_post_json", fake_post)
    await provider.complete(
        [
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": "hi"},
        ]
    )


@pytest.mark.asyncio
async def test_anthropic_stream_yields_chunks(monkeypatch):
    provider = AnthropicProvider("sk-ant-test")

    class FakeResponse:
        status_code = 200

        async def aread(self):
            return b""

        async def aiter_lines(self):
            for line in [
                'data: {"type":"message_start","message":{"usage":{"input_tokens":3}}}',
                'data: {"type":"content_block_delta","delta":{"text":"Hi"}}',
                'data: {"type":"message_delta","usage":{"output_tokens":2}}',
            ]:
                yield line

    class FakeStream:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *args):
            return None

    class FakeClient:
        def stream(self, *args, **kwargs):
            return FakeStream()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(
        "runtime.adapters.providers.anthropic.httpx.AsyncClient",
        lambda **kwargs: FakeClient(),
    )

    chunks = []
    async for chunk in provider.stream([{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    assert chunks == ["Hi"]
    assert provider.last_usage is not None
    assert provider.last_usage.provider == "anthropic"
