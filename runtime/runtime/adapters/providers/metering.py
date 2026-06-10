from __future__ import annotations

from collections.abc import AsyncIterator

from core.domain.usage import LlmUsage
from core.ports.provider import ProviderPort
from runtime.adapters.providers.usage_helpers import estimate_usage


class MeteringProvider:
    """Wraps a ProviderPort and records LlmUsage after each complete/stream call."""

    def __init__(self, inner: ProviderPort, *, provider: str, model: str) -> None:
        self._inner = inner
        self._provider_kind = provider
        self._model = model
        self._pending: list[LlmUsage] = []

    async def complete(self, messages: list[dict], **kwargs) -> str:
        text = await self._inner.complete(messages, **kwargs)
        usage = self._collect_usage(messages, text)
        self._pending.append(usage)
        return text

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        output_parts: list[str] = []
        async for token in self._inner.stream(messages, **kwargs):
            output_parts.append(token)
            yield token
        usage = self._collect_usage(messages, "".join(output_parts))
        self._pending.append(usage)

    def pop_usage(self) -> LlmUsage | None:
        if not self._pending:
            return None
        return self._pending.pop(0)

    def drain_usages(self) -> list[LlmUsage]:
        items = list(self._pending)
        self._pending.clear()
        return items

    @property
    def inner(self) -> ProviderPort:
        return self._inner

    def _collect_usage(self, messages: list[dict], output: str) -> LlmUsage:
        inner = self._inner
        if hasattr(inner, "inner"):
            inner = inner.inner  # ProviderRouter
        last = getattr(inner, "last_usage", None)
        if isinstance(last, LlmUsage):
            return last
        model = getattr(inner, "_model", self._model)
        return estimate_usage(
            messages,
            output,
            provider=self._provider_kind,
            model=model or self._model,
        )
