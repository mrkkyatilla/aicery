from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from gateway.adapters.db.repositories import OrgRepository
from gateway.adapters.db.session import get_db
from gateway.config import Settings
from gateway.services.auth import InvalidApiKeyError, TenantContext, resolve_tenant
from gateway.services.jwt_auth import GatewayJwtError, decode_tenant_token
from gateway.services.rate_limit import GatewayRateLimitedError, check_rate_limit

SessionDep = Annotated[Session, Depends(get_db)]


async def require_tenant(
    request: Request,
    session: SessionDep,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    authorization: str | None = Header(default=None),
) -> TenantContext:
    settings = Settings()
    tenant: TenantContext | None = None

    if x_api_key:
        try:
            tenant = resolve_tenant(session, x_api_key)
        except InvalidApiKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc
    elif settings.jwt_enabled and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header",
            )
        try:
            org_id = decode_tenant_token(token, settings=settings)
        except GatewayJwtError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc
        org = OrgRepository(session).get(org_id)
        if org is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Org not found")
        tenant = TenantContext(org=org, api_key=None)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Api-Key or Bearer token",
        )

    request.state.tenant_org_id = tenant.org_id
    try:
        await check_rate_limit(str(tenant.org_id))
    except GatewayRateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": str(exc.error_code),
                "message": str(exc),
            },
        ) from exc
    return tenant


async def require_admin(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> None:
    if x_admin_token != Settings().admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


async def require_internal(
    x_internal_secret: str = Header(..., alias="X-Internal-Secret"),
) -> None:
    if x_internal_secret != Settings().internal_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal secret")


TenantDep = Annotated[TenantContext, Depends(require_tenant)]
