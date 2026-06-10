import pytest

from core.domain.replay import ReplayContext, ReplayMode


def test_replay_requires_source_run_id() -> None:
    with pytest.raises(ValueError, match="source_run_id"):
        ReplayContext(mode=ReplayMode.REPLAY)


def test_replay_sets_mock_provider() -> None:
    ctx = ReplayContext(
        mode=ReplayMode.REPLAY,
        source_run_id="550e8400-e29b-41d4-a716-446655440000",
        mock_tools=True,
    )
    assert ctx.mock_provider is True
    assert ctx.is_replay
