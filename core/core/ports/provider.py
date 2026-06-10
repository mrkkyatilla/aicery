from collections.abc import AsyncIterator
from typing import Protocol


class ProviderPort(Protocol):
    async def complete(self, messages: list[dict], **kwargs) -> str: ...

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]: ...
