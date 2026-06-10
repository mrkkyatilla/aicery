from __future__ import annotations

from collections.abc import AsyncIterator

from runtime.adapters.providers.errors import ProviderError


class FailingProvider:
    """Test double: always fails (T3-E6-03 failover)."""

    async def complete(self, messages: list[dict], **kwargs) -> str:
        raise ProviderError("primary provider unavailable")

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        raise ProviderError("primary provider unavailable")
        if False:  # pragma: no cover
            yield ""
