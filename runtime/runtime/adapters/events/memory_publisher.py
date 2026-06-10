from core.events.validate import validate_envelope


class InMemoryEventPublisher:
    """Test double — records validated event envelopes."""

    def __init__(self) -> None:
        self.published: list[dict] = []

    async def publish(self, subject: str, payload: dict) -> None:
        validate_envelope(payload)
        assert payload["subject"] == subject
        self.published.append(payload)
