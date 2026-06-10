from __future__ import annotations

from agents.manifest import tool_requires_approval
from core.domain.hitl import ApprovalDecision
from core.ports.tool_executor import ToolExecutorPort
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.config import Settings
from runtime.errors import HitlApprovalPending
from runtime.services.hitl_coordinator import HitlCoordinator
from tools.registry.executor import ToolPermissionDenied


class ApprovalToolExecutor:
    """Pauses tool calls that require human approval (HITL)."""

    def __init__(
        self,
        inner: ToolExecutorPort,
        *,
        agent_id: str,
        approval_repo: ApprovalRepository,
        session=None,
        settings: Settings | None = None,
    ) -> None:
        self._inner = inner
        self._agent_id = agent_id
        self._repo = approval_repo
        self._settings = settings or Settings()
        db_session = session if session is not None else approval_repo._session  # noqa: SLF001
        self._coordinator = HitlCoordinator(db_session, settings=self._settings)

    def _hitl_active(self, tool_name: str) -> bool:
        if not self._settings.hitl_enabled:
            return False
        return tool_requires_approval(self._agent_id, tool_name)

    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str | None = None,
    ) -> dict:
        if not self._hitl_active(tool_name):
            return await self._inner.invoke(
                tool_name,
                arguments,
                run_id=run_id,
                agent_id=agent_id,
                workspace_root=workspace_root,
            )

        resolved = self._repo.get_resolved_for_run_tool(run_id, tool_name)
        if resolved is not None:
            if resolved.decision == ApprovalDecision.REJECT:
                raise ToolPermissionDenied("Human rejected tool execution")
            final_args = resolved.final_arguments if resolved.final_arguments is not None else arguments
            return await self._inner.invoke(
                tool_name,
                final_args,
                run_id=run_id,
                agent_id=agent_id,
                workspace_root=workspace_root,
            )

        open_approval = self._repo.get_open_for_run(run_id)
        if open_approval is not None and open_approval.tool_name == tool_name:
            pending = open_approval
        else:
            pending = self._coordinator.create_executor_pending(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
                agent_id=agent_id,
            )

        raise HitlApprovalPending(
            approval_id=pending.approval_id,
            tool_name=tool_name,
            arguments=pending.arguments,
            expires_at=pending.expires_at.isoformat(),
        )
