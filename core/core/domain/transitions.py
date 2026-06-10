from core.domain.errors import InvalidStateTransitionError
from core.domain.run import RunStatus

ALLOWED_TRANSITIONS: frozenset[tuple[RunStatus, RunStatus]] = frozenset(
    {
        (RunStatus.PENDING, RunStatus.RUNNING),
        (RunStatus.PENDING, RunStatus.CANCELLED),
        (RunStatus.RUNNING, RunStatus.COMPLETED),
        (RunStatus.RUNNING, RunStatus.FAILED),
        (RunStatus.RUNNING, RunStatus.CANCELLED),
        (RunStatus.RUNNING, RunStatus.SUSPENDED),
        (RunStatus.SUSPENDED, RunStatus.RUNNING),
        (RunStatus.SUSPENDED, RunStatus.CANCELLED),
        (RunStatus.SUSPENDED, RunStatus.FAILED),
    }
)


def assert_transition(current: RunStatus, target: RunStatus) -> None:
    if (current, target) not in ALLOWED_TRANSITIONS:
        raise InvalidStateTransitionError(current.value, target.value)
