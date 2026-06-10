from sqlalchemy.orm import Session

from core.ports.trace import TracePort
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.adapters.trace.memory import InMemoryTracePort
from runtime.config import Settings

_memory_port: InMemoryTracePort | None = None


def get_trace_port(session: Session | None = None) -> TracePort:
    url = Settings().database_url
    if url.startswith("sqlite://") and session is None:
        global _memory_port
        if _memory_port is None:
            _memory_port = InMemoryTracePort()
        return _memory_port
    if session is None:
        from runtime.adapters.db.session import get_session_factory

        session = get_session_factory()()
        try:
            return TraceRepository(session)
        finally:
            session.close()
    return TraceRepository(session)


def reset_memory_trace_port() -> None:
    global _memory_port
    _memory_port = None
