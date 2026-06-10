from fastapi import HTTPException, Request, status

from core.domain.replay import ReplayContext, ReplayMode
from core.trace.hashing import hash_text
from runtime.adapters.db.repository import RunRepository
from runtime.adapters.db.session import get_session_factory


def parse_replay_context(request: Request) -> ReplayContext:
    mode_header = request.headers.get("X-Aicery-Replay-Mode", "live").lower()
    mode = ReplayMode.REPLAY if mode_header == "replay" else ReplayMode.LIVE
    mock_tools = request.headers.get("X-Aicery-Mock-Tools", "").lower() == "true"
    source_run_id = request.headers.get("X-Aicery-Source-Run-Id")
    try:
        return ReplayContext(
            mode=mode,
            source_run_id=source_run_id,
            mock_tools=mock_tools,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def validate_replay_input(source_run_id: str, input_text: str) -> None:
    factory = get_session_factory()
    session = factory()
    try:
        source = RunRepository(session).get(source_run_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Source run not found")
        if hash_text(source.input_text) != hash_text(input_text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="REPLAY_INPUT_MISMATCH",
            )
    finally:
        session.close()
