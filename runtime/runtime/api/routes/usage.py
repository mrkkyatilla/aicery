from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.domain.usage import RunUsageSummary
from runtime.adapters.db.repository import RunRepository
from runtime.adapters.db.session import get_db
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.api.auth import require_auth
from runtime.services.usage_service import summarize_run_usage

router = APIRouter(
    prefix="/runs",
    tags=["usage"],
    dependencies=[Depends(require_auth)],
)


class UsageLineResponse(BaseModel):
    step_id: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int


class RunUsageResponse(BaseModel):
    run_id: str
    tokens_in: int
    tokens_out: int
    llm_calls: int
    lines: list[UsageLineResponse] = Field(default_factory=list)


def _to_response(summary: RunUsageSummary) -> RunUsageResponse:
    return RunUsageResponse(
        run_id=summary.run_id,
        tokens_in=summary.tokens_in,
        tokens_out=summary.tokens_out,
        llm_calls=summary.llm_calls,
        lines=[
            UsageLineResponse(
                step_id=line.step_id,
                provider=line.provider,
                model=line.model,
                tokens_in=line.tokens_in,
                tokens_out=line.tokens_out,
            )
            for line in summary.lines
        ],
    )


@router.get("/{run_id}/usage", response_model=RunUsageResponse)
def get_run_usage(run_id: str, session: Session = Depends(get_db)) -> RunUsageResponse:
    if RunRepository(session).get(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = TraceRepository(session).list_by_run(run_id)
    return _to_response(summarize_run_usage(run_id, steps))
