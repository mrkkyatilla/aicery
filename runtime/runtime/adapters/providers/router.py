from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from core.domain.usage import LlmUsage
from core.ports.provider import ProviderPort
from runtime.adapters.providers.errors import ProviderError

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Primary provider with fallback on ProviderError (E2 F3)."""

    def __init__(self, primary: ProviderPort, fallback: ProviderPort) -> None:
        self._primary = primary
        self._fallback = fallback
        self.last_usage: LlmUsage | None = None

    @property
    def inner(self) -> ProviderPort:
        return self._primary

    async def complete(self, messages: list[dict], **kwargs) -> str:
        try:
            result = await self._primary.complete(messages, **kwargs)
            self.last_usage = getattr(self._primary, "last_usage", None)
            return result
        except ProviderError as exc:
            logger.warning(
                "provider.failover",
                extra={"reason": str(exc), "team": "E2"},
            )
            result = await self._fallback.complete(messages, **kwargs)
            self.last_usage = getattr(self._fallback, "last_usage", None)
            return result

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            async for token in self._primary.stream(messages, **kwargs):
                yield token
            self.last_usage = getattr(self._primary, "last_usage", None)
        except ProviderError as exc:
            logger.warning(
                "provider.failover.stream",
                extra={"reason": str(exc), "team": "E2"},
            )
            async for token in self._fallback.stream(messages, **kwargs):
                yield token
            self.last_usage = getattr(self._fallback, "last_usage", None)
