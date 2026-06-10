import asyncio
import time
from collections.abc import Callable

from core.domain.tool import ToolCallRecord
from tools.registry import REGISTRY
from tools.sandbox.jail import PathTraversalError


class ToolPermissionDenied(Exception):
    error_code = "TOOL_PERMISSION_DENIED"


class ToolTimeout(Exception):
    error_code = "TOOL_TIMEOUT"


class ToolNotFound(Exception):
    error_code = "TOOL_NOT_FOUND"


RETRYABLE_TOOLS = frozenset({"search_workspace", "http_request"})
MAX_RETRIES = 2


class RegistryToolExecutor:
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        workspace_root: str = ".",
        allowed_tools: list[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._workspace_root = workspace_root
        self._allowed = set(allowed_tools or [])
        self._timeout = timeout

    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str | None = None,
    ) -> dict:
        if self._allowed and tool_name not in self._allowed:
            raise ToolPermissionDenied(f"Tool not allowed: {tool_name}")

        definition = REGISTRY.get(tool_name)
        if definition is None:
            raise ToolNotFound(f"Unknown tool: {tool_name}")

        root = workspace_root or self._workspace_root
        started = time.monotonic()
        attempts = MAX_RETRIES + 1 if tool_name in RETRYABLE_TOOLS else 1
        last_timeout: TimeoutError | None = None
        for attempt in range(attempts):
            try:
                result = await asyncio.wait_for(
                    self._run_handler(definition.handler, arguments, root),
                    timeout=self._timeout,
                )
                duration_ms = int((time.monotonic() - started) * 1000)
                return {"result": result, "duration_ms": duration_ms}
            except TimeoutError as exc:
                last_timeout = exc
                if attempt + 1 < attempts:
                    continue
            except PathTraversalError:
                raise
        if last_timeout is not None:
            raise ToolTimeout(f"Tool {tool_name} timed out") from last_timeout
        raise ToolTimeout(f"Tool {tool_name} timed out")

    async def _run_handler(
        self, handler: Callable[..., dict], arguments: dict, workspace_root: str
    ) -> dict:
        return await asyncio.to_thread(
            handler,
            **arguments,
            workspace_root=workspace_root,
        )

    def to_record(
        self, run_id: str, tool_name: str, arguments: dict, outcome: dict
    ) -> ToolCallRecord:
        return ToolCallRecord(
            run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
            result=outcome.get("result"),
            error_code=outcome.get("error_code"),
            duration_ms=outcome.get("duration_ms", 0),
        )
