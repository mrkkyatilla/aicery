from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from runtime.config import Settings

_saver: BaseCheckpointSaver | None = None
_pool = None
_setup_done = False


def _checkpoint_enabled(settings: Settings) -> bool:
    if not settings.langgraph_checkpoint_enabled:
        return False
    return True


def _is_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _to_psycopg_conn_string(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgresql://"):
        return database_url
    raise ValueError(f"Unsupported database URL for LangGraph checkpoints: {database_url}")


def _memory_checkpointer() -> BaseCheckpointSaver:
    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()


async def get_checkpointer(settings: Settings | None = None) -> BaseCheckpointSaver:
    """Return a LangGraph checkpointer (Postgres, memory, or in-memory fallback)."""
    global _saver, _pool, _setup_done
    settings = settings or Settings()

    if not _checkpoint_enabled(settings):
        return _memory_checkpointer()

    backend = settings.langgraph_checkpoint_backend.lower()
    if backend == "memory" or _is_sqlite(settings.database_url):
        if _saver is None:
            _saver = _memory_checkpointer()
        return _saver

    if _saver is not None:
        return _saver

    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    conn_string = _to_psycopg_conn_string(settings.database_url)
    _pool = AsyncConnectionPool(
        conn_string,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await _pool.open()
    _saver = AsyncPostgresSaver(_pool)
    if not _setup_done:
        await _saver.setup()
        _setup_done = True
    return _saver


async def reset_checkpointer() -> None:
    """Close pooled connections (tests)."""
    global _saver, _pool, _setup_done
    if _pool is not None:
        await _pool.close()
    _saver = None
    _pool = None
    _setup_done = False
