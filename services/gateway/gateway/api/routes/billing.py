from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gateway.api.deps import SessionDep, TenantDep
from gateway.services.billing import billing_summary, create_checkout_session

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    tier: str = Field(pattern="^(pro|team)$")


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


@router.get("/me")
def billing_me(tenant: TenantDep, session: SessionDep) -> dict:
    return billing_summary(session, tenant.org_id)


@router.get("/usage")
def billing_usage(tenant: TenantDep, session: SessionDep, period: str = "current") -> dict:
    if period != "current":
        raise HTTPException(status_code=400, detail="Only period=current supported")
    summary = billing_summary(session, tenant.org_id)
    return {"period": period, "usage": summary["usage"], "limits": summary["limits"]}


@router.post("/checkout", response_model=CheckoutResponse)
def billing_checkout(
    body: CheckoutRequest, tenant: TenantDep, session: SessionDep
) -> CheckoutResponse:
    try:
        result = create_checkout_session(session, tenant.org_id, body.tier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckoutResponse(url=result["url"], session_id=result["session_id"])
