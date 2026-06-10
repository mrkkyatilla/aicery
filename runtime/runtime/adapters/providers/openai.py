from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from core.domain.usage import LlmUsage
from runtime.adapters.providers.errors import ProviderError, TransientProviderError
from runtime.adapters.providers.usage_helpers import (
    estimate_usage,
    usage_from_openai_response,
)


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        base_url: str = "https://api.openai.com/v1",
        provider_name: str = "openai",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._provider_name = provider_name
        self.last_usage: LlmUsage | None = None

    async def complete(self, messages: list[dict], **kwargs) -> str:
        model = kwargs.get("model") or self._model
        payload = {
            "model": model,
            "messages": [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
        }
        data = await self._post_json("/chat/completions", payload)
        try:
            content = str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Invalid OpenAI response: {data}") from exc
        self.last_usage = usage_from_openai_response(
            data, provider=self._provider_name, model=model
        ) or estimate_usage(
            messages, content, provider=self._provider_name, model=model
        )
        return content

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        model = kwargs.get("model") or self._model
        payload = {
            "model": model,
            "messages": [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        output_parts: list[str] = []
        stream_usage: dict | None = None
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 500:
                        raise TransientProviderError(f"OpenAI {response.status_code}")
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise ProviderError(f"OpenAI {response.status_code}: {body[:200]}")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        chunk = line[5:].strip()
                        if chunk == "[DONE]":
                            break
                        try:
                            parsed = json.loads(chunk)
                            if isinstance(parsed.get("usage"), dict):
                                stream_usage = parsed["usage"]
                            delta = parsed["choices"][0]["delta"].get("content")
                            if delta:
                                output_parts.append(delta)
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
            except httpx.TimeoutException as exc:
                raise TransientProviderError("OpenAI timeout") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(str(exc)) from exc
        text = "".join(output_parts)
        if stream_usage:
            self.last_usage = LlmUsage(
                provider=self._provider_name,
                model=model,
                tokens_in=int(stream_usage.get("prompt_tokens", 0) or 0),
                tokens_out=int(stream_usage.get("completion_tokens", 0) or 0),
            )
        else:
            self.last_usage = estimate_usage(
                messages, text, provider=self._provider_name, model=model
            )

    async def _post_json(self, path: str, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self._base_url}{path}",
                    headers=headers,
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                raise TransientProviderError("OpenAI timeout") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(str(exc)) from exc
        if response.status_code >= 500:
            raise TransientProviderError(f"OpenAI {response.status_code}")
        if response.status_code >= 400:
            raise ProviderError(f"OpenAI {response.status_code}: {response.text[:200]}")
        return response.json()
