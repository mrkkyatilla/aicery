from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from core.domain.usage import LlmUsage
from runtime.adapters.providers.errors import ProviderError, TransientProviderError
from runtime.adapters.providers.usage_helpers import estimate_usage

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022") -> None:
        self._api_key = api_key
        self._model = model
        self.last_usage: LlmUsage | None = None

    async def complete(self, messages: list[dict], **kwargs) -> str:
        model = kwargs.get("model") or self._model
        system, anthropic_messages = _split_messages(messages)
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system:
            payload["system"] = system
        data = await self._post_json("/messages", payload)
        try:
            content = str(data["content"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Invalid Anthropic response: {data}") from exc
        usage = data.get("usage") or {}
        tokens_in = int(usage.get("input_tokens", 0) or 0)
        tokens_out = int(usage.get("output_tokens", 0) or 0)
        if tokens_in or tokens_out:
            self.last_usage = LlmUsage(
                provider="anthropic",
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
        else:
            self.last_usage = estimate_usage(
                messages, content, provider="anthropic", model=model
            )
        return content

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        model = kwargs.get("model") or self._model
        system, anthropic_messages = _split_messages(messages)
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "stream": True,
        }
        if system:
            payload["system"] = system

        output_parts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{ANTHROPIC_BASE_URL}/messages",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 500:
                        raise TransientProviderError(f"Anthropic {response.status_code}")
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise ProviderError(f"Anthropic {response.status_code}: {body[:200]}")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        chunk = line[5:].strip()
                        if not chunk:
                            continue
                        try:
                            parsed = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
                        event_type = parsed.get("type")
                        if event_type == "content_block_delta":
                            delta = parsed.get("delta") or {}
                            text = delta.get("text")
                            if text:
                                output_parts.append(text)
                                yield text
                        elif event_type == "message_delta":
                            usage = (parsed.get("usage") or {})
                            output_tokens = int(usage.get("output_tokens", output_tokens) or 0)
                        elif event_type == "message_start":
                            msg = parsed.get("message") or {}
                            usage = msg.get("usage") or {}
                            input_tokens = int(usage.get("input_tokens", input_tokens) or 0)
            except httpx.TimeoutException as exc:
                raise TransientProviderError("Anthropic timeout") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(str(exc)) from exc

        text = "".join(output_parts)
        self.last_usage = LlmUsage(
            provider="anthropic",
            model=model,
            tokens_in=input_tokens,
            tokens_out=output_tokens or max(1, len(text.split())),
        )
        if self.last_usage.tokens_in == 0 and self.last_usage.tokens_out == 0:
            self.last_usage = estimate_usage(messages, text, provider="anthropic", model=model)

    async def _post_json(self, path: str, payload: dict) -> dict:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{ANTHROPIC_BASE_URL}{path}",
                    headers=headers,
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                raise TransientProviderError("Anthropic timeout") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(str(exc)) from exc
        if response.status_code >= 500:
            raise TransientProviderError(f"Anthropic {response.status_code}")
        if response.status_code >= 400:
            raise ProviderError(f"Anthropic {response.status_code}: {response.text[:200]}")
        return response.json()


def _split_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
    system_parts: list[str] = []
    anthropic_messages: list[dict] = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if role == "system":
            system_parts.append(content)
            continue
        if role not in ("user", "assistant"):
            role = "user"
        anthropic_messages.append({"role": role, "content": content})
    if not anthropic_messages:
        anthropic_messages = [{"role": "user", "content": ""}]
    system = "\n".join(system_parts) if system_parts else None
    return system, anthropic_messages
