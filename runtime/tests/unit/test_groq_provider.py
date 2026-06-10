import pytest

from runtime.adapters.providers.groq import GROQ_BASE_URL, GroqProvider


@pytest.mark.asyncio
async def test_groq_complete_uses_api_response(monkeypatch):
    provider = GroqProvider("gsk-test", model="llama-3.3-70b-versatile")

    async def fake_post(_path: str, _payload: dict) -> dict:
        return {
            "choices": [{"message": {"content": "Hello from Groq"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }

    monkeypatch.setattr(provider, "_post_json", fake_post)
    text = await provider.complete([{"role": "user", "content": "hi"}])
    assert text == "Hello from Groq"
    assert provider.last_usage is not None
    assert provider.last_usage.provider == "groq"
    assert provider.last_usage.model == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_groq_stream_yields_chunks(monkeypatch):
    provider = GroqProvider("gsk-test")

    class FakeResponse:
        status_code = 200

        async def aread(self):
            return b""

        async def aiter_lines(self):
            for line in [
                'data: {"choices":[{"delta":{"content":"Hi"}}]}',
                "data: [DONE]",
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
        "runtime.adapters.providers.openai.httpx.AsyncClient",
        lambda **kwargs: FakeClient(),
    )

    chunks = []
    async for chunk in provider.stream([{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    assert chunks == ["Hi"]
    assert provider.last_usage is not None
    assert provider.last_usage.provider == "groq"


def test_groq_base_url():
    provider = GroqProvider("gsk-test")
    assert provider._base_url == GROQ_BASE_URL.rstrip("/")
    assert provider._provider_name == "groq"
