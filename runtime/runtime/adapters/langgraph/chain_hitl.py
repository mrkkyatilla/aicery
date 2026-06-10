from __future__ import annotations

from typing import Any

from agents.manifest import tool_requires_approval
from core.domain.replay import ReplayContext
from core.domain.run import Run
from core.ports.tool_executor import ToolExecutorPort
from langgraph.types import interrupt
from runtime.config import Settings
from tools.registry.executor import ToolPermissionDenied


def _parse_resume_value(resume_value: Any, default_arguments: dict) -> tuple[str, dict]:
    if resume_value is None:
        return "approve", default_arguments
    if isinstance(resume_value, dict):
        decision = str(resume_value.get("decision", "approve")).lower()
        if decision == "modify" and resume_value.get("arguments") is not None:
            return decision, dict(resume_value["arguments"])
        return decision, default_arguments
    if isinstance(resume_value, str):
        return resume_value.lower(), default_arguments
    return "approve", default_arguments


async def invoke_tool_with_hitl(
    tool_name: str,
    arguments: dict,
    *,
    tools: ToolExecutorPort,
    run: Run,
    node: str,
    replay_ctx: ReplayContext | None = None,
    graph: str | None = None,
) -> dict:
    """Invoke a tool, pausing with LangGraph interrupt() when manifest requires approval."""
    settings = Settings()
    skip = replay_ctx is not None and replay_ctx.is_replay
    if (
        not skip
        and settings.hitl_enabled
        and tool_requires_approval(run.agent_id, tool_name)
    ):
        resume_value = interrupt(
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "node": node,
                "graph": graph or "research-chain",
            }
        )
        decision, final_args = _parse_resume_value(resume_value, arguments)
        if decision == "reject":
            raise ToolPermissionDenied("Human rejected tool execution")
        arguments = final_args

    return await tools.invoke(
        tool_name,
        arguments,
        run_id=run.id,
        agent_id=run.agent_id,
    )
