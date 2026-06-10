import json
import logging

from core.events.validate import validate_envelope

logger = logging.getLogger(__name__)


class NatsEventPublisher:
    def __init__(self, nc) -> None:
        self._nc = nc

    async def publish(self, subject: str, payload: dict) -> None:
        validate_envelope(payload)
        assert payload["subject"] == subject
        await self._nc.publish(subject, json.dumps(payload).encode("utf-8"))
