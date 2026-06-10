
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agents.graphs.chain_research import build_research_chain_graph
from agents.manifest import load_manifest, tool_requires_approval
from core.domain.run import Run
from runtime.adapters.providers.mock import MockProvider


class _StubTools:
    async def invoke(self, tool_name, arguments, *, run_id, agent_id, workspace_root=None):
        if tool_name == "search_workspace":
            return {"result": {"hits": [{"file": "README.md"}]}, "duration_ms": 1}
        if tool_name == "read_file":
            return {"result": {"content": "file body"}, "duration_ms": 1}
        raise AssertionError(f"unexpected tool {tool_name}")


@pytest.fixture(autouse=True)
def _clear_manifest_cache():
    load_manifest.cache_clear()
    yield
    load_manifest.cache_clear()


def test_research_manifest_read_file_requires_approval() -> None:
    assert tool_requires_approval("research", "read_file") is True
    assert tool_requires_approval("research", "search_workspace") is False


@pytest.mark.asyncio
async def test_chain_interrupts_before_read_file(monkeypatch) -> None:
    monkeypatch.setenv("HITL_ENABLED", "true")
    run = Run(agent_id="research", input_text="summarize")
    checkpointer = InMemorySaver()
    graph = build_research_chain_graph(
        MockProvider(),
        _StubTools(),
        run,
        checkpointer=checkpointer,
    )
    config = {"configurable": {"thread_id": run.id}}

    chunks: list = []
    async for chunk in graph.astream(
        {"messages": [{"role": "user", "content": run.input_text}], "artifacts": {}, "step_index": 0},
        config,
        stream_mode="updates",
    ):
        chunks.append(chunk)

    assert any("__interrupt__" in c for c in chunks)
    intr = next(c["__interrupt__"][0] for c in chunks if "__interrupt__" in c)
    assert intr.value["tool_name"] == "read_file"
    assert intr.value["node"] == "executor"

    resume_chunks: list = []
    async for chunk in graph.astream(Command(resume={"decision": "approve"}), config, stream_mode="updates"):
        resume_chunks.append(chunk)

    assert any("summarizer" in c for c in resume_chunks)
    final = await graph.aget_state(config)
    assert final.values.get("step_index", 0) >= 3
