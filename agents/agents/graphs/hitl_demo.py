from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from core.domain.replay import ReplayContext
from core.domain.run import Run
from core.ports.tool_executor import ToolExecutorPort
from runtime.adapters.langgraph.chain_hitl import invoke_tool_with_hitl


class HitlDemoState(TypedDict):
    messages: list[dict]
    step_index: int


def build_hitl_demo_graph(
    provider,
    tools: ToolExecutorPort | None = None,
    run: Run | None = None,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    replay_ctx: ReplayContext | None = None,
):
    del provider
    if tools is None or run is None:
        raise ValueError("hitl-demo requires tools and run")

    ctx = replay_ctx or ReplayContext()

    async def probe(state: HitlDemoState) -> dict:
        outcome = await invoke_tool_with_hitl(
            "hitl_probe",
            {"action": "demo", "target": run.input_text[:80]},
            tools=tools,
            run=run,
            node="hitl_probe",
            replay_ctx=ctx,
            graph="hitl-demo",
        )
        result = outcome.get("result", outcome)
        message = f"Approved action completed: {result}"
        return {
            "messages": [*state["messages"], {"role": "assistant", "content": message}],
            "step_index": state.get("step_index", 0) + 1,
        }

    graph = StateGraph(HitlDemoState)
    graph.add_node("hitl_probe", probe)
    graph.set_entry_point("hitl_probe")
    graph.add_edge("hitl_probe", END)
    return graph.compile(checkpointer=checkpointer)
