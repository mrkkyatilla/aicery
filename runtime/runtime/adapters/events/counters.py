"""In-process event counters per run (F1 gate; durable store → F3)."""

from collections import defaultdict

_events_per_run: dict[str, int] = defaultdict(int)


def increment_event_count(run_id: str) -> int:
    _events_per_run[run_id] += 1
    return _events_per_run[run_id]


def get_event_count(run_id: str) -> int:
    return _events_per_run.get(run_id, 0)


def reset_event_counters() -> None:
    _events_per_run.clear()
