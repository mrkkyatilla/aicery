from typing import TypedDict

from langgraph.graph import END, StateGraph

from core.domain.run import Run
from core.ports.provider import ProviderPort
from core.ports.tool_executor import ToolExecutorPort


class EchoState(TypedDict):
    messages: list[dict]


def build_echo_graph(
    provider: ProviderPort,
    tools: ToolExecutorPort | None = None,
    run: Run | None = None,
):
    async def llm_node(state: EchoState) -> dict:
        text = await provider.complete(state["messages"])
        return {"messages": [*state["messages"], {"role": "assistant", "content": text}]}

    graph = StateGraph(EchoState)
    graph.add_node("llm", llm_node)
    graph.set_entry_point("llm")
    graph.add_edge("llm", END)
    return graph.compile()
