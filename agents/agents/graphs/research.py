from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.graphs.research_paths import resolve_research_file_path
from core.domain.run import Run
from core.ports.provider import ProviderPort
from core.ports.tool_executor import ToolExecutorPort


class ResearchState(TypedDict):
    messages: list[dict]
    tool_calls_count: int


def build_research_graph(
    provider: ProviderPort,
    tools: ToolExecutorPort | None = None,
    run: Run | None = None,
):
    if tools is None or run is None:
        raise ValueError("research agent requires tools and run context")

    async def research_node(state: ResearchState) -> dict:
        user_text = state["messages"][-1]["content"]
        path = await resolve_research_file_path(
            user_text,
            tools,
            run_id=run.id,
            agent_id=run.agent_id,
        )
        outcome = await tools.invoke(
            "read_file",
            {"path": path},
            run_id=run.id,
            agent_id=run.agent_id,
        )
        content = outcome["result"]["content"]
        summary = await provider.complete(
            [
                {
                    "role": "system",
                    "content": "Summarize the file content concisely for the user.",
                },
                {"role": "user", "content": content[:8000]},
            ]
        )
        return {
            "messages": [
                *state["messages"],
                {"role": "assistant", "content": summary},
            ],
            "tool_calls_count": state.get("tool_calls_count", 0) + 1,
        }

    graph = StateGraph(ResearchState)
    graph.add_node("research", research_node)
    graph.set_entry_point("research")
    graph.add_edge("research", END)
    return graph.compile()
