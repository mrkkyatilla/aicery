from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.domain.trace import TraceStepType
from core.domain.usage import LlmUsage
from runtime.adapters.db.session import get_db
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.api.auth import require_auth
from runtime.services.usage_service import usage_from_step_metadata

router = APIRouter(
    prefix="/runs",
    tags=["trace"],
    dependencies=[Depends(require_auth)],
)


class TraceUsageResponse(BaseModel):
    provider: str
    model: str
    tokens_in: int
    tokens_out: int


class TraceStepResponse(BaseModel):
    step_id: str
    type: str
    name: str
    parent_step_id: str | None
    started_at: str
    ended_at: str | None
    status: str
    duration_ms: int | None
    input_hash: str
    output_hash: str | None = None
    error_code: str | None = None
    usage: TraceUsageResponse | None = None


class TraceResponse(BaseModel):
    run_id: str
    steps: list[TraceStepResponse]


def _duration_ms(started, ended) -> int | None:
    if ended is None:
        return None
    delta = ended - started
    return int(delta.total_seconds() * 1000)


@router.get("/{run_id}/trace", response_model=TraceResponse)
def get_run_trace(run_id: str, session: Session = Depends(get_db)) -> TraceResponse:
    from runtime.adapters.db.repository import RunRepository

    if RunRepository(session).get(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    steps = TraceRepository(session).list_by_run(run_id)
    responses: list[TraceStepResponse] = []
    for s in steps:
        usage: LlmUsage | None = usage_from_step_metadata(s) if s.type == TraceStepType.LLM else None
        responses.append(
            TraceStepResponse(
                step_id=s.step_id,
                type=s.type.value if isinstance(s.type, TraceStepType) else str(s.type),
                name=s.name,
                parent_step_id=s.parent_step_id,
                started_at=s.started_at.astimezone(UTC).isoformat(),
                ended_at=s.ended_at.astimezone(UTC).isoformat() if s.ended_at else None,
                status=s.status,
                duration_ms=_duration_ms(s.started_at, s.ended_at),
                input_hash=s.input_hash,
                output_hash=s.output_hash,
                error_code=s.error_code,
                usage=(
                    TraceUsageResponse(
                        provider=usage.provider,
                        model=usage.model,
                        tokens_in=usage.tokens_in,
                        tokens_out=usage.tokens_out,
                    )
                    if usage
                    else None
                ),
            )
        )
    return TraceResponse(run_id=run_id, steps=responses)
