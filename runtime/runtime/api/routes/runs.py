from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.domain.hitl import ApprovalDecision
from core.domain.run import Run, RunCreate
from runtime.api.auth import require_auth
from runtime.api.deps import RunServiceDep
from runtime.api.policy_models import ProviderPolicyBody, to_domain_policy
from runtime.services.policy_resolver import resolve_provider_policy, validate_resolved_policy

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    dependencies=[Depends(require_auth)],
)


class CreateRunRequest(BaseModel):
    agent_id: str | None = None
    input: str
    workspace_id: str | None = None
    host_workspace_root: str | None = None
    pipeline: str | None = None
    conversation_id: str | None = None
    execute: bool = True
    provider_policy: ProviderPolicyBody | None = None


class RunResponse(BaseModel):
    id: str
    status: str
    agent_id: str
    created_at: str
    conversation_id: str | None = None
    input_text: str | None = None
    output_text: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    tool_calls_count: int | None = None
    events_count: int | None = None

    @classmethod
    def from_run(
        cls,
        run: Run,
        *,
        tool_calls_count: int | None = None,
        events_count: int | None = None,
    ) -> "RunResponse":
        return cls(
            id=run.id,
            status=run.status.value,
            agent_id=run.agent_id,
            created_at=run.created_at.isoformat(),
            conversation_id=run.conversation_id,
            input_text=run.input_text,
            output_text=run.output_text,
            error_code=run.error_code,
            error_message=run.error_message,
            tool_calls_count=tool_calls_count,
            events_count=events_count,
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RunResponse)
async def create_run(body: CreateRunRequest, service: RunServiceDep) -> RunResponse:
    if not body.agent_id and not body.pipeline:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="agent_id or pipeline required",
        )
    agent_id = body.agent_id or ("research" if body.pipeline else "echo")
    request_policy = to_domain_policy(body.provider_policy)
    try:
        resolved = resolve_provider_policy(request_policy=request_policy, agent_id=agent_id)
        validate_resolved_policy(resolved)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    run = await service.create_run(
        RunCreate(
            agent_id=agent_id,
            input_text=body.input,
            workspace_id=body.workspace_id,
            host_workspace_root=body.host_workspace_root,
            pipeline_id=body.pipeline,
            conversation_id=body.conversation_id,
            provider_policy=resolved,
        ),
        execute=body.execute,
    )
    return RunResponse.from_run(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, service: RunServiceDep) -> RunResponse:
    run, tool_calls_count, events_count = await service.get_run_metrics(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse.from_run(
        run,
        tool_calls_count=tool_calls_count,
        events_count=events_count,
    )


class ResumeRunRequest(BaseModel):
    decision: Literal["approve", "reject", "modify"]
    approval_id: str | None = None
    arguments: dict | None = None


@router.post("/{run_id}/resume", response_model=RunResponse)
async def resume_run(
    run_id: str,
    body: ResumeRunRequest,
    service: RunServiceDep,
) -> RunResponse:
    try:
        decision = ApprovalDecision(body.decision)
        run = await service.resume_run(
            run_id,
            decision=decision,
            approval_id=body.approval_id,
            arguments=body.arguments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse.from_run(run)
