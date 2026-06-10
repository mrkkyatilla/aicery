from __future__ import annotations

from runtime.adapters.providers.openai import OpenAIProvider

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(OpenAIProvider):
    """Groq chat completions (OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        super().__init__(
            api_key,
            model=model,
            base_url=GROQ_BASE_URL,
            provider_name="groq",
        )
