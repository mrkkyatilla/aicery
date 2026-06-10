from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from gateway.adapters.db.repositories import OrgRepository, SubscriptionRepository, UsageRepository
from gateway.config import Settings
from gateway.domain.tiers import TIER_LIMITS, normalize_tier


def ingest_usage_payload(session: Session, payload: dict[str, Any]) -> uuid.UUID | None:
    """CP-2 webhook: map workspace_id to org and record usage_events."""
    from gateway.adapters.db.models import WorkspaceORM
    from gateway.adapters.db.repositories import UsageRepository
    from sqlalchemy import select

    run_id = str(payload.get("run_id", ""))
    workspace_id = payload.get("workspace_id")
    if not run_id:
        return None

    org_id: uuid.UUID | None = None
    if workspace_id:
        row = session.scalar(
            select(WorkspaceORM).where(WorkspaceORM.runtime_workspace_id == str(workspace_id))
        )
        if row:
            org_id = row.org_id

    if org_id is None:
        from gateway.adapters.db.models import RunLinkORM

        link = session.get(RunLinkORM, run_id)
        if link:
            org_id = link.org_id

    if org_id is None:
        return None

    repo = UsageRepository(session)
    tokens_in = float(payload.get("tokens_in", 0) or 0)
    tokens_out = float(payload.get("tokens_out", 0) or 0)
    repo.record(
        org_id=org_id,
        workspace_id=str(workspace_id) if workspace_id else None,
        run_id=run_id,
        metric="agent_run",
        quantity=1,
    )
    if tokens_in > 0:
        repo.record(
            org_id=org_id,
            workspace_id=str(workspace_id) if workspace_id else None,
            run_id=run_id,
            metric="llm_tokens_in",
            quantity=tokens_in,
            unit="token",
        )
    if tokens_out > 0:
        repo.record(
            org_id=org_id,
            workspace_id=str(workspace_id) if workspace_id else None,
            run_id=run_id,
            metric="llm_tokens_out",
            quantity=tokens_out,
            unit="token",
        )
    return org_id


def billing_summary(session: Session, org_id: uuid.UUID) -> dict[str, Any]:
    org = OrgRepository(session).get(org_id)
    tier = normalize_tier(org.tier if org else "free")
    limits = TIER_LIMITS[tier]
    usage = UsageRepository(session).aggregate_for_org(org_id)
    sub = SubscriptionRepository(session).get_for_org(org_id)
    return {
        "org_id": str(org_id),
        "name": org.name if org else "",
        "tier": tier,
        "stripe_customer_id": org.stripe_customer_id if org else None,
        "subscription_status": sub.status if sub else "inactive",
        "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        "usage": usage,
        "limits": limits,
    }


def create_checkout_session(session: Session, org_id: uuid.UUID, tier: str) -> dict[str, str]:
    settings = Settings()
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY not configured")
    price_id = settings.stripe_price_pro if tier == "pro" else settings.stripe_price_team
    if tier not in ("pro", "team") or not price_id:
        raise ValueError("Invalid tier or missing STRIPE_PRICE_* env")

    import stripe

    stripe.api_key = settings.stripe_secret_key
    org = OrgRepository(session).get(org_id)
    if org is None:
        raise ValueError("Org not found")

    customer_id = org.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(name=org.name, metadata={"org_id": str(org_id)})
        customer_id = customer.id
        OrgRepository(session).set_stripe_customer(org_id, customer_id)

    session_obj = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.checkout_success_url,
        cancel_url=settings.checkout_cancel_url,
        metadata={"org_id": str(org_id), "tier": tier},
    )
    return {"url": session_obj.url or "", "session_id": session_obj.id}
