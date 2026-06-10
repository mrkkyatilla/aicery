from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from core.domain.replay import ReplayContext
from core.domain.run import Run
from core.ports.provider import ProviderPort
from core.ports.tool_executor import ToolExecutorPort
from runtime.adapters.langgraph.chain_hitl import invoke_tool_with_hitl
from runtime.errors import GraphStepLimitError
from runtime.observability.graph_policy_context import get_max_graph_steps


class ChainState(TypedDict):
    messages: list[dict]
    artifacts: dict
    step_index: int


def build_research_chain_graph(
    provider: ProviderPort,
    tools: ToolExecutorPort | None = None,
    run: Run | None = None,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    replay_ctx: ReplayContext | None = None,
):
    if tools is None or run is None:
        raise ValueError("research-chain requires tools and run")

    max_steps = get_max_graph_steps()
    ctx = replay_ctx or ReplayContext()

    def _check_step_limit(state: ChainState) -> None:
        if state.get("step_index", 0) >= max_steps:
            raise GraphStepLimitError()

    async def planner(state: ChainState) -> dict:
        _check_step_limit(state)
        hits: list = []
        try:
            outcome = await invoke_tool_with_hitl(
                "search_workspace",
                {"query": run.input_text[:80], "path": "."},
                tools=tools,
                run=run,
                node="planner",
                replay_ctx=ctx,
            )
            hits = outcome["result"].get("hits", [])
        except Exception:
            hits = []
        plan = f"Found {len(hits)} hits. Read top file and summarize."
        return {
            "messages": [*state["messages"], {"role": "assistant", "content": plan}],
            "artifacts": {"hits": hits, "plan": plan},
            "step_index": state.get("step_index", 0) + 1,
        }

    async def executor(state: ChainState) -> dict:
        _check_step_limit(state)
        path = "README.md"
        hits = state.get("artifacts", {}).get("hits", [])
        if hits:
            path = hits[0].get("file", path)
        outcome = await invoke_tool_with_hitl(
            "read_file",
            {"path": path},
            tools=tools,
            run=run,
            node="executor",
            replay_ctx=ctx,
        )
        content = outcome["result"].get("content", "")[:4000]
        return {
            "messages": [*state["messages"], {"role": "assistant", "content": content}],
            "artifacts": {**state.get("artifacts", {}), "file": path, "content": content},
            "step_index": state.get("step_index", 0) + 1,
        }

    async def summarizer(state: ChainState) -> dict:
        _check_step_limit(state)
        content = state.get("artifacts", {}).get("content", run.input_text)
        summary = await provider.complete(
            [
                {"role": "system", "content": "Summarize for the user."},
                {"role": "user", "content": content},
            ]
        )
        return {
            "messages": [*state["messages"], {"role": "assistant", "content": summary}],
            "step_index": state.get("step_index", 0) + 1,
        }

    graph = StateGraph(ChainState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("summarizer", summarizer)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "summarizer")
    graph.add_edge("summarizer", END)
    return graph.compile(checkpointer=checkpointer)
