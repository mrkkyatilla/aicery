from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from gateway.adapters.db.repositories import OrgRepository, SubscriptionRepository
from gateway.config import Settings


def tier_from_price_id(settings: Settings, price_id: str | None) -> str | None:
    if not price_id:
        return None
    if price_id == settings.stripe_price_pro:
        return "pro"
    if price_id == settings.stripe_price_team:
        return "team"
    return None


def handle_stripe_event(session: Session, event: dict[str, Any]) -> None:
    settings = Settings()
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        org_id_str = (data.get("metadata") or {}).get("org_id")
        tier = (data.get("metadata") or {}).get("tier", "pro")
        if org_id_str:
            OrgRepository(session).update_tier(uuid.UUID(org_id_str), tier)
        return

    if event_type in ("customer.subscription.updated", "customer.subscription.created"):
        org_id = _org_id_from_subscription(session, data, settings)
        if org_id is None:
            return
        price_id = _first_price_id(data)
        tier = tier_from_price_id(settings, price_id) or "pro"
        status = data.get("status", "active")
        if status in ("active", "trialing"):
            OrgRepository(session).update_tier(org_id, tier)
        period_end = data.get("current_period_end")
        end_dt = datetime.fromtimestamp(period_end, tz=UTC) if period_end else None
        SubscriptionRepository(session).upsert(
            org_id=org_id,
            stripe_subscription_id=data.get("id"),
            status=status,
            price_id=price_id,
            current_period_end=end_dt,
        )
        return

    if event_type == "customer.subscription.deleted":
        org_id = _org_id_from_subscription(session, data, settings)
        if org_id:
            OrgRepository(session).update_tier(org_id, "free")
            SubscriptionRepository(session).upsert(
                org_id=org_id,
                stripe_subscription_id=data.get("id"),
                status="canceled",
                price_id=_first_price_id(data),
                current_period_end=None,
            )
        return

    if event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        if customer_id:
            from gateway.adapters.db.models import OrgORM
            from sqlalchemy import select

            org = session.scalar(select(OrgORM).where(OrgORM.stripe_customer_id == customer_id))
            if org:
                OrgRepository(session).update_tier(org.id, "past_due")


def _first_price_id(subscription: dict) -> str | None:
    items = subscription.get("items", {}).get("data", [])
    if items:
        return items[0].get("price", {}).get("id")
    return subscription.get("plan", {}).get("id")


def _org_id_from_subscription(
    session: Session, data: dict, settings: Settings
) -> uuid.UUID | None:
    meta = data.get("metadata") or {}
    if meta.get("org_id"):
        return uuid.UUID(meta["org_id"])
    customer_id = data.get("customer")
    if not customer_id:
        return None
    from gateway.adapters.db.models import OrgORM
    from sqlalchemy import select

    org = session.scalar(select(OrgORM).where(OrgORM.stripe_customer_id == customer_id))
    return org.id if org else None
