"""SDK surface matches OpenAPI v1 routes."""

import inspect

from aicery_sdk import AiceryClient


def test_client_exposes_v1_methods() -> None:
    assert hasattr(AiceryClient, "create_run")
    assert hasattr(AiceryClient, "get_run")
    assert hasattr(AiceryClient, "list_agents")
    assert hasattr(AiceryClient, "stream_run")
    assert hasattr(AiceryClient, "from_config")

    sig = inspect.signature(AiceryClient.create_run)
    assert "pipeline" in sig.parameters
    assert "agent_id" in sig.parameters
