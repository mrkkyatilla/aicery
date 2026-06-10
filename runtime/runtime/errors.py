from core.domain.error_codes import ErrorCode


class GraphStepLimitError(Exception):
    error_code = ErrorCode.GRAPH_STEP_LIMIT

    def __init__(self, message: str = "Graph step limit exceeded") -> None:
        super().__init__(message)


class HitlApprovalPending(Exception):
    """Raised when a tool call must wait for human approval."""

    error_code = ErrorCode.HITL_APPROVAL_REQUIRED

    def __init__(
        self,
        *,
        approval_id: str,
        tool_name: str,
        arguments: dict,
        expires_at: str,
    ) -> None:
        self.approval_id = approval_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.expires_at = expires_at
        super().__init__(f"Approval required for tool {tool_name}")
