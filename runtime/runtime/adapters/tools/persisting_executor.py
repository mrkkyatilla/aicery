import time

from core.domain.tool import ToolCallRecord
from runtime.adapters.db.session import get_session_factory
from runtime.adapters.db.tool_call_repository import ToolCallRepository
from tools.registry.executor import (
    RegistryToolExecutor,
    ToolNotFound,
    ToolPermissionDenied,
    ToolTimeout,
)


class PersistingToolExecutor:
    """Wraps registry executor with allowlist + Postgres tool_calls persistence (E2/E4)."""

    def __init__(
        self,
        *,
        workspace_root: str,
        allowed_tools: list[str],
        agent_id: str,
        timeout: float = RegistryToolExecutor.DEFAULT_TIMEOUT,
    ) -> None:
        self._agent_id = agent_id
        self._inner = RegistryToolExecutor(
            workspace_root=workspace_root,
            allowed_tools=allowed_tools,
            timeout=timeout,
        )

    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str | None = None,
    ) -> dict:
        started = time.monotonic()
        record = ToolCallRecord(
            run_id=run_id,
            tool_name=tool_name,
            arguments=arguments,
        )
        try:
            outcome = await self._inner.invoke(
                tool_name,
                arguments,
                run_id=run_id,
                agent_id=agent_id or self._agent_id,
                workspace_root=workspace_root,
            )
            record.result = outcome.get("result")
            record.duration_ms = outcome.get("duration_ms", 0)
            self._persist(record)
            await self._emit_tool_called(
                run_id=run_id,
                agent_id=agent_id or self._agent_id,
                tool_name=tool_name,
                arguments=arguments,
                duration_ms=record.duration_ms,
                success=True,
            )
            return outcome
        except (ToolPermissionDenied, ToolTimeout, ToolNotFound) as exc:
            record.error_code = exc.error_code
            record.duration_ms = int((time.monotonic() - started) * 1000)
            self._persist(record)
            await self._emit_tool_called(
                run_id=run_id,
                agent_id=agent_id or self._agent_id,
                tool_name=tool_name,
                arguments=arguments,
                duration_ms=record.duration_ms,
                success=False,
                error_code=exc.error_code,
            )
            raise
        except Exception as exc:
            record.error_code = getattr(exc, "error_code", "TOOL_ERROR")
            record.duration_ms = int((time.monotonic() - started) * 1000)
            self._persist(record)
            await self._emit_tool_called(
                run_id=run_id,
                agent_id=agent_id or self._agent_id,
                tool_name=tool_name,
                arguments=arguments,
                duration_ms=record.duration_ms,
                success=False,
                error_code=record.error_code,
            )
            raise

    async def _emit_tool_called(self, **kwargs) -> None:
        from runtime.adapters.events.tool_events import emit_tool_called

        await emit_tool_called(**kwargs)

    def _persist(self, record: ToolCallRecord) -> None:
        factory = get_session_factory()
        session = factory()
        try:
            ToolCallRepository(session).append(record)
        finally:
            session.close()
