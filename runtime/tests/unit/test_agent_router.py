from runtime.services.agent_router import route_input


def test_route_echo_short_greeting():
    result = route_input("hello there")
    assert result.agent_id == "echo"
    assert result.confidence >= 0.7


def test_route_research_summarize():
    result = route_input("Summarize examples/research-docs/docs/golden-scope.md for me")
    assert result.agent_id == "research"
    assert result.confidence >= 0.5
