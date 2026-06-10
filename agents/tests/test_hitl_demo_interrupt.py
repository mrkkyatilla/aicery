
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agents.graphs.hitl_demo import build_hitl_demo_graph
from core.domain.run import Run
from runtime.adapters.providers.mock import MockProvider


class _StubTools:
    async def invoke(self, tool_name, arguments, *, run_id, agent_id, workspace_root=None):
        return {"result": {"ok": True, "action": arguments.get("action")}, "duration_ms": 1}


@pytest.mark.asyncio
async def test_hitl_demo_graph_interrupts_before_probe() -> None:
    run = Run(agent_id="hitl-demo", input_text="demo probe")
    graph = build_hitl_demo_graph(
        MockProvider(),
        _StubTools(),
        run,
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": run.id}}

    chunks: list = []
    async for chunk in graph.astream(
        {"messages": [{"role": "user", "content": run.input_text}], "step_index": 0},
        config,
        stream_mode="updates",
    ):
        chunks.append(chunk)

    assert any("__interrupt__" in c for c in chunks)
    intr = next(c["__interrupt__"][0] for c in chunks if "__interrupt__" in c)
    assert intr.value["tool_name"] == "hitl_probe"
    assert intr.value["graph"] == "hitl-demo"

    async for chunk in graph.astream(Command(resume={"decision": "approve"}), config, stream_mode="updates"):
        assert "__interrupt__" not in chunk

    final = await graph.aget_state(config)
    assert final.values.get("step_index", 0) >= 1
