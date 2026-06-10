import pytest

from agents.graphs.echo import build_echo_graph
from runtime.adapters.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_echo_graph_mock_provider() -> None:
    graph = build_echo_graph(MockProvider())
    result = await graph.ainvoke({"messages": [{"role": "user", "content": "ping"}]})
    assert result["messages"][-1]["content"] == "echo:ping"
