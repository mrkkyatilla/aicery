from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from runtime.config import Settings

_engine = None
_SessionLocal = None


def get_engine(database_url: str | None = None):
    global _engine, _SessionLocal
    url = database_url or Settings().database_url
    if _engine is None or str(_engine.url) != url:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        pool_kwargs: dict = {}
        if url.startswith("sqlite") and (url == "sqlite://" or ":memory:" in url):
            pool_kwargs["poolclass"] = StaticPool
        elif url.startswith("postgresql"):
            pool_kwargs["pool_size"] = 10
            pool_kwargs["max_overflow"] = 40
            pool_kwargs["pool_timeout"] = 30
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args=connect_args,
            **pool_kwargs,
        )
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    get_engine(database_url)
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
