from typing import Protocol


class ToolExecutorPort(Protocol):
    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str,
    ) -> dict: ...
