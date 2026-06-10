from core.domain.run import Run
from core.events import build_envelope, validate_envelope
from core.events.envelope import envelope_to_dict
from core.ports.events import EventPublisherPort
from runtime.adapters.events.counters import increment_event_count


class RunEventEmitter:
    def __init__(self, publisher: EventPublisherPort) -> None:
        self._publisher = publisher

    async def emit(self, subject: str, run: Run, payload: dict) -> None:
        envelope = build_envelope(subject, run, payload)
        data = envelope_to_dict(envelope)
        validate_envelope(data)
        await self._publisher.publish(subject, data)
        increment_event_count(run.id)
