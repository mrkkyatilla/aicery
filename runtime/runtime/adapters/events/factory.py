import logging

from core.ports.events import EventPublisherPort
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.events.nats_publisher import NatsEventPublisher
from runtime.config import Settings

logger = logging.getLogger(__name__)
_publisher: EventPublisherPort | None = None
_test_publisher: EventPublisherPort | None = None


def set_test_publisher(publisher: EventPublisherPort | None) -> None:
    """Tests: route tool.called and other emits through the same publisher as FastAPI deps."""
    global _publisher, _test_publisher
    _test_publisher = publisher
    _publisher = publisher


async def get_event_publisher() -> EventPublisherPort:
    global _publisher
    if _test_publisher is not None:
        return _test_publisher
    if _publisher is not None:
        return _publisher

    settings = Settings()
    if not settings.nats_enabled:
        _publisher = InMemoryEventPublisher()
        return _publisher

    try:
        import nats

        nc = await nats.connect(settings.nats_url)
        _publisher = NatsEventPublisher(nc)
        logger.info("Connected to NATS at %s", settings.nats_url)
    except Exception as exc:
        logger.warning("NATS unavailable (%s); using in-memory publisher", exc)
        _publisher = InMemoryEventPublisher()
    return _publisher


def reset_event_publisher() -> None:
    global _publisher, _test_publisher
    _publisher = None
    _test_publisher = None
