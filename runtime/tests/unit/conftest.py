import pytest

from runtime.api.rate_limit import reset_rate_limiter


@pytest.fixture(autouse=True)
def unit_tests_use_memory_rate_limit(monkeypatch):
    """Unit tests must not require a live Redis for API key rate limiting."""
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.fixture(autouse=True)
def unit_tests_disable_semantic_search(monkeypatch):
    """Avoid Qdrant client recursion / connection noise in API unit tests."""
    monkeypatch.setenv("SEMANTIC_SEARCH_ENABLED", "false")


@pytest.fixture(autouse=True)
def unit_tests_disable_jwt(monkeypatch):
    monkeypatch.setenv("JWT_ENABLED", "false")
