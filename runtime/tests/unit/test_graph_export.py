from agents.graph_export import list_graph_keys, render_graph, render_graph_mermaid
from agents.graph_export import render_graph as rg


def test_list_graph_keys_includes_builtins() -> None:
    keys = list_graph_keys()
    assert "echo" in keys
    assert "research" in keys
    assert "research-chain" in keys


def test_render_echo_graph() -> None:
    text = render_graph("echo")
    assert "echo" in text
    assert "llm" in text


def test_render_chain_graph() -> None:
    text = rg("research-chain")
    assert "planner" in text
    assert "summarizer" in text


def test_render_chain_graph_mermaid() -> None:
    text = render_graph_mermaid("research-chain")
    assert "flowchart LR" in text
    assert "planner" in text
    assert "executor" in text
    assert "summarizer" in text
    assert "planner --> executor" in text
    assert "executor --> summarizer" in text
