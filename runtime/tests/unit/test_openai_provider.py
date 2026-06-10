import pytest

from runtime.adapters.providers.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_complete_uses_api_response(monkeypatch):
    provider = OpenAIProvider("sk-test", model="gpt-4o-mini")

    async def fake_post(_path: str, _payload: dict) -> dict:
        return {"choices": [{"message": {"content": "Hello from GPT"}}]}

    monkeypatch.setattr(provider, "_post_json", fake_post)
    text = await provider.complete([{"role": "user", "content": "hi"}])
    assert text == "Hello from GPT"
