from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from runtime.api.auth import require_auth
from runtime.config import Settings
from runtime.services.index_job_service import get_index_job_service, should_enqueue_async

router = APIRouter(
    prefix="/workspace",
    tags=["workspace"],
    dependencies=[Depends(require_auth)],
)


class IndexWorkspaceRequest(BaseModel):
    workspace_id: str = Field(default="local")
    paths: list[str] = Field(default_factory=lambda: ["guide/"])
    file_metadata: dict[str, dict[str, str]] = Field(default_factory=dict)


class IndexWorkspaceResponse(BaseModel):
    workspace_id: str
    files_indexed: int
    chunks_upserted: int
    duration_ms: int


class IndexJobAcceptedResponse(BaseModel):
    job_id: str
    status: str = "pending"


class IndexJobStatusResponse(BaseModel):
    job_id: str
    status: str
    workspace_id: str
    paths: list[str]
    result: IndexWorkspaceResponse | None = None
    error_message: str | None = None


@router.post(
    "/index",
    responses={
        200: {"model": IndexWorkspaceResponse},
        202: {"model": IndexJobAcceptedResponse},
    },
)
async def index_workspace_route(
    body: IndexWorkspaceRequest,
    async_mode: bool = Query(False, alias="async"),
):
    settings = Settings()
    if not settings.semantic_search_enabled:
        raise HTTPException(status_code=503, detail="Semantic search disabled")

    if should_enqueue_async(body.paths, async_requested=async_mode):
        job_id = get_index_job_service().enqueue_index(
            body.workspace_id,
            body.paths,
            workspace_root=settings.workspace_root,
            file_metadata=body.file_metadata,
        )
        payload = IndexJobAcceptedResponse(job_id=job_id)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=payload.model_dump(),
        )

    from runtime.intelligence.indexer import index_workspace

    try:
        result = await index_workspace(
            body.workspace_id,
            body.paths,
            workspace_root=settings.workspace_root,
            file_metadata=body.file_metadata,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return IndexWorkspaceResponse(
        workspace_id=result.workspace_id,
        files_indexed=result.files_indexed,
        chunks_upserted=result.chunks_upserted,
        duration_ms=result.duration_ms,
    )


@router.get("/index/jobs/{job_id}", response_model=IndexJobStatusResponse)
async def get_index_job_route(job_id: str) -> IndexJobStatusResponse:
    job = await get_index_job_service().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result = None
    if job.result is not None:
        result = IndexWorkspaceResponse(
            workspace_id=job.result.workspace_id,
            files_indexed=job.result.files_indexed,
            chunks_upserted=job.result.chunks_upserted,
            duration_ms=job.result.duration_ms,
        )
    return IndexJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        workspace_id=job.workspace_id,
        paths=job.paths,
        result=result,
        error_message=job.error_message,
    )
