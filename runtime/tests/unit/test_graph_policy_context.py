from runtime.observability.graph_policy_context import (
    get_max_graph_steps,
    reset_max_graph_steps,
    set_max_graph_steps,
)


def test_max_graph_steps_override(monkeypatch):
    monkeypatch.setenv("MAX_GRAPH_STEPS", "20")
    token = set_max_graph_steps(3)
    try:
        assert get_max_graph_steps() == 3
    finally:
        reset_max_graph_steps(token)
    assert get_max_graph_steps() == 20
