from typing import Protocol


class EventPublisherPort(Protocol):
    async def publish(self, subject: str, payload: dict) -> None: ...
