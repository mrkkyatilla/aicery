from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from gateway.adapters.db.repositories import ApiKeyRepository, OrgRepository, WorkspaceRepository
from gateway.api.deps import SessionDep, require_admin
from gateway.services.auth import generate_api_key, hash_api_key

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class CreateOrgRequest(BaseModel):
    name: str = Field(min_length=1)


class CreateOrgResponse(BaseModel):
    id: str
    name: str
    tier: str


class CreateApiKeyResponse(BaseModel):
    id: str
    key: str
    key_prefix: str
    name: str


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1)
    runtime_workspace_id: str | None = None


class CreateWorkspaceResponse(BaseModel):
    id: str
    runtime_workspace_id: str
    name: str


class UpdateOrgRequest(BaseModel):
    max_graph_steps: int | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    tier: str
    max_graph_steps: int | None = None


@router.post("/orgs", response_model=CreateOrgResponse)
def create_org(body: CreateOrgRequest, session: SessionDep) -> CreateOrgResponse:
    org = OrgRepository(session).create(body.name)
    return CreateOrgResponse(id=str(org.id), name=org.name, tier=org.tier)


@router.post("/orgs/{org_id}/api-keys", response_model=CreateApiKeyResponse)
def create_api_key(org_id: str, session: SessionDep, name: str = "default") -> CreateApiKeyResponse:
    oid = uuid.UUID(org_id)
    if OrgRepository(session).get(oid) is None:
        raise HTTPException(status_code=404, detail="Org not found")
    plaintext = generate_api_key()
    prefix = plaintext[:12]
    row = ApiKeyRepository(session).create(
        org_id=oid,
        key_hash=hash_api_key(plaintext),
        key_prefix=prefix,
        name=name,
    )
    return CreateApiKeyResponse(
        id=str(row.id),
        key=plaintext,
        key_prefix=prefix,
        name=row.name,
    )


@router.patch("/orgs/{org_id}", response_model=OrgResponse)
def update_org(org_id: str, body: UpdateOrgRequest, session: SessionDep) -> OrgResponse:
    oid = uuid.UUID(org_id)
    org = OrgRepository(session).update_max_graph_steps(oid, body.max_graph_steps)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    return OrgResponse(
        id=str(org.id),
        name=org.name,
        tier=org.tier,
        max_graph_steps=org.max_graph_steps,
    )


@router.post("/orgs/{org_id}/workspaces", response_model=CreateWorkspaceResponse)
def create_workspace(
    org_id: str, body: CreateWorkspaceRequest, session: SessionDep
) -> CreateWorkspaceResponse:
    oid = uuid.UUID(org_id)
    if OrgRepository(session).get(oid) is None:
        raise HTTPException(status_code=404, detail="Org not found")
    runtime_id = body.runtime_workspace_id or str(uuid.uuid4())
    row = WorkspaceRepository(session).create(
        org_id=oid, name=body.name, runtime_workspace_id=runtime_id
    )
    return CreateWorkspaceResponse(
        id=str(row.id), runtime_workspace_id=row.runtime_workspace_id, name=row.name
    )
