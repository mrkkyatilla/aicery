from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry import trace
from sqlalchemy.orm import Session

from gateway.adapters.aicery.client import AiceryRuntimeClient
from gateway.adapters.db.repositories import RunLinkRepository, WorkspaceRepository
from gateway.api.deps import SessionDep, TenantDep
from gateway.services.auth import TenantContext
from gateway.services.quota import QuotaExceededError, check_run_quota

router = APIRouter(prefix="/v1", tags=["proxy"])


def _tenant_headers(tenant: TenantContext) -> dict[str, str]:
    headers = {"X-Aicery-Org-Id": str(tenant.org_id)}
    if tenant.org.max_graph_steps is not None:
        headers["X-Aicery-Max-Steps"] = str(tenant.org.max_graph_steps)
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("aicery.org_id", str(tenant.org_id))
    return headers


def _resolve_workspace(
    session: Session, tenant: TenantDep, body: dict[str, Any]
) -> tuple[str, uuid.UUID]:
    ws_repo = WorkspaceRepository(session)
    runtime_ws = body.get("workspace_id")
    if runtime_ws:
        row = ws_repo.get_by_runtime_id(tenant.org_id, str(runtime_ws))
        if row is None:
            raise HTTPException(status_code=400, detail="Unknown workspace_id for this org")
        return row.runtime_workspace_id, row.id
    default = ws_repo.get_default(tenant.org_id)
    if default is None:
        raise HTTPException(
            status_code=400,
            detail="No workspace configured; POST /admin/orgs/{id}/workspaces first",
        )
    return default.runtime_workspace_id, default.id


def _ensure_run_access(session: Session, tenant: TenantDep, run_id: str) -> None:
    link = RunLinkRepository(session).get(run_id)
    if link is None or link.org_id != tenant.org_id:
        raise HTTPException(status_code=404, detail="Run not found")


@router.post("/route")
async def proxy_route(request: Request, tenant: TenantDep) -> JSONResponse:
    body = await request.json()
    client = AiceryRuntimeClient()
    response = await client.request("POST", "/v1/route", json=body)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.post("/runs")
async def proxy_create_run(
    request: Request, tenant: TenantDep, session: SessionDep
) -> JSONResponse:
    try:
        check_run_quota(session, tenant.org_id)
    except QuotaExceededError as exc:
        return JSONResponse(
            status_code=402,
            content={
                "type": "about:blank",
                "title": "Quota Exceeded",
                "status": 402,
                "detail": str(exc),
                "error_code": exc.error_code,
                "metric": exc.metric,
                "limit": exc.limit,
                "used": exc.used,
            },
        )
    body = await request.json()
    runtime_ws, workspace_uuid = _resolve_workspace(session, tenant, body)
    body = {**body, "workspace_id": runtime_ws}
    client = AiceryRuntimeClient()
    response = await client.request(
        "POST",
        "/v1/runs",
        json=body,
        extra_headers=_tenant_headers(tenant),
    )
    if response.status_code == 201:
        data = response.json()
        run_id = data.get("id")
        if run_id:
            RunLinkRepository(session).create(
                run_id=run_id,
                org_id=tenant.org_id,
                workspace_id=workspace_uuid,
            )
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/runs/{run_id}")
async def proxy_get_run(
    run_id: str, tenant: TenantDep, session: SessionDep
) -> JSONResponse:
    _ensure_run_access(session, tenant, run_id)
    client = AiceryRuntimeClient()
    headers = _tenant_headers(tenant)
    response = await client.request("GET", f"/v1/runs/{run_id}", extra_headers=headers)
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/runs/{run_id}/usage")
async def proxy_get_usage(
    run_id: str, tenant: TenantDep, session: SessionDep
) -> JSONResponse:
    _ensure_run_access(session, tenant, run_id)
    client = AiceryRuntimeClient()
    response = await client.request(
        "GET",
        f"/v1/runs/{run_id}/usage",
        extra_headers=_tenant_headers(tenant),
    )
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/runs/{run_id}/trace")
async def proxy_get_trace(
    run_id: str, tenant: TenantDep, session: SessionDep
) -> JSONResponse:
    _ensure_run_access(session, tenant, run_id)
    client = AiceryRuntimeClient()
    response = await client.request(
        "GET",
        f"/v1/runs/{run_id}/trace",
        extra_headers=_tenant_headers(tenant),
    )
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/runs/{run_id}/stream")
async def proxy_stream_run(
    run_id: str, tenant: TenantDep, session: SessionDep
) -> StreamingResponse:
    _ensure_run_access(session, tenant, run_id)
    client = AiceryRuntimeClient()
    http_client, response = await client.stream_request(
        f"/v1/runs/{run_id}/stream",
        extra_headers=_tenant_headers(tenant),
    )
    if response.status_code >= 400:
        body = await response.aread()
        await http_client.aclose()
        raise HTTPException(status_code=response.status_code, detail=body.decode()[:200])

    async def event_generator():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await http_client.aclose()

    return StreamingResponse(
        event_generator(),
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "text/event-stream"),
    )


@router.post("/runs/{run_id}/resume")
async def proxy_resume_run(
    run_id: str,
    request: Request,
    tenant: TenantDep,
    session: SessionDep,
) -> JSONResponse:
    _ensure_run_access(session, tenant, run_id)
    body = await request.json()
    client = AiceryRuntimeClient()
    response = await client.request(
        "POST",
        f"/v1/runs/{run_id}/resume",
        json=body,
        extra_headers=_tenant_headers(tenant),
    )
    return JSONResponse(status_code=response.status_code, content=response.json())


@router.get("/agents")
async def proxy_agents(tenant: TenantDep) -> JSONResponse:
    del tenant
    client = AiceryRuntimeClient()
    response = await client.request("GET", "/v1/agents")
    return JSONResponse(status_code=response.status_code, content=response.json())
