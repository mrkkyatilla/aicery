from core.domain.error_codes import ErrorCode


class InvalidStateTransitionError(Exception):
    error_code = ErrorCode.INVALID_STATE_TRANSITION

    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition from {from_status} to {to_status}")


class ReplayMismatchError(Exception):
    error_code = ErrorCode.REPLAY_MISMATCH

    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class ReplayInputMismatchError(Exception):
    error_code = ErrorCode.REPLAY_INPUT_MISMATCH

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
