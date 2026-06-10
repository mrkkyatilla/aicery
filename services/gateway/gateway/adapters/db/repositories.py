from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gateway.adapters.db.models import (
    ApiKeyORM,
    OrgORM,
    RunLinkORM,
    SubscriptionORM,
    UsageEventORM,
    WorkspaceORM,
)


class OrgRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, name: str) -> OrgORM:
        row = OrgORM(name=name, tier="free", created_at=datetime.now(UTC))
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, org_id: uuid.UUID) -> OrgORM | None:
        return self._session.get(OrgORM, org_id)

    def update_tier(self, org_id: uuid.UUID, tier: str) -> OrgORM | None:
        row = self.get(org_id)
        if row is None:
            return None
        row.tier = tier
        self._session.commit()
        self._session.refresh(row)
        return row

    def update_max_graph_steps(self, org_id: uuid.UUID, max_graph_steps: int | None) -> OrgORM | None:
        row = self.get(org_id)
        if row is None:
            return None
        row.max_graph_steps = max_graph_steps
        self._session.commit()
        self._session.refresh(row)
        return row

    def set_stripe_customer(self, org_id: uuid.UUID, customer_id: str) -> None:
        row = self.get(org_id)
        if row is None:
            return
        row.stripe_customer_id = customer_id
        self._session.commit()


class ApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, org_id: uuid.UUID, key_hash: str, key_prefix: str, name: str) -> ApiKeyORM:
        row = ApiKeyORM(
            org_id=org_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_active_for_org(self, org_id: uuid.UUID) -> list[ApiKeyORM]:
        stmt = select(ApiKeyORM).where(ApiKeyORM.org_id == org_id, ApiKeyORM.revoked_at.is_(None))
        return list(self._session.scalars(stmt).all())

    def list_all_active(self) -> list[ApiKeyORM]:
        stmt = select(ApiKeyORM).where(ApiKeyORM.revoked_at.is_(None))
        return list(self._session.scalars(stmt).all())


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, *, org_id: uuid.UUID, name: str, runtime_workspace_id: str
    ) -> WorkspaceORM:
        row = WorkspaceORM(
            org_id=org_id,
            name=name,
            runtime_workspace_id=runtime_workspace_id,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, workspace_id: uuid.UUID) -> WorkspaceORM | None:
        return self._session.get(WorkspaceORM, workspace_id)

    def get_by_runtime_id(self, org_id: uuid.UUID, runtime_workspace_id: str) -> WorkspaceORM | None:
        stmt = select(WorkspaceORM).where(
            WorkspaceORM.org_id == org_id,
            WorkspaceORM.runtime_workspace_id == runtime_workspace_id,
        )
        return self._session.scalar(stmt)

    def list_for_org(self, org_id: uuid.UUID) -> list[WorkspaceORM]:
        stmt = select(WorkspaceORM).where(WorkspaceORM.org_id == org_id)
        return list(self._session.scalars(stmt).all())

    def get_default(self, org_id: uuid.UUID) -> WorkspaceORM | None:
        workspaces = self.list_for_org(org_id)
        return workspaces[0] if workspaces else None


class RunLinkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, run_id: str, org_id: uuid.UUID, workspace_id: uuid.UUID) -> RunLinkORM:
        row = RunLinkORM(
            run_id=run_id,
            org_id=org_id,
            workspace_id=workspace_id,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        return row

    def get(self, run_id: str) -> RunLinkORM | None:
        return self._session.get(RunLinkORM, run_id)


class SubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self,
        *,
        org_id: uuid.UUID,
        stripe_subscription_id: str | None,
        status: str,
        price_id: str | None,
        current_period_end: datetime | None,
    ) -> SubscriptionORM:
        row = self._session.scalar(select(SubscriptionORM).where(SubscriptionORM.org_id == org_id))
        now = datetime.now(UTC)
        if row is None:
            row = SubscriptionORM(
                org_id=org_id,
                stripe_subscription_id=stripe_subscription_id,
                status=status,
                price_id=price_id,
                current_period_end=current_period_end,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.stripe_subscription_id = stripe_subscription_id
            row.status = status
            row.price_id = price_id
            row.current_period_end = current_period_end
            row.updated_at = now
        self._session.commit()
        self._session.refresh(row)
        return row

    def get_for_org(self, org_id: uuid.UUID) -> SubscriptionORM | None:
        return self._session.scalar(select(SubscriptionORM).where(SubscriptionORM.org_id == org_id))


class UsageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        org_id: uuid.UUID,
        workspace_id: str | None,
        run_id: str,
        metric: str,
        quantity: float,
        unit: str = "count",
    ) -> UsageEventORM | None:
        existing = self._session.scalar(
            select(UsageEventORM).where(
                UsageEventORM.run_id == run_id,
                UsageEventORM.metric == metric,
            )
        )
        if existing is not None:
            return existing
        row = UsageEventORM(
            org_id=org_id,
            workspace_id=workspace_id,
            run_id=run_id,
            metric=metric,
            quantity=Decimal(str(quantity)),
            unit=unit,
            recorded_at=datetime.now(UTC),
        )
        self._session.add(row)
        try:
            self._session.commit()
            self._session.refresh(row)
            return row
        except Exception:
            self._session.rollback()
            return self._session.scalar(
                select(UsageEventORM).where(
                    UsageEventORM.run_id == run_id,
                    UsageEventORM.metric == metric,
                )
            )

    def sum_month(self, org_id: uuid.UUID, metric: str) -> float:
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.coalesce(func.sum(UsageEventORM.quantity), 0)).where(
            UsageEventORM.org_id == org_id,
            UsageEventORM.metric == metric,
            UsageEventORM.recorded_at >= start,
        )
        total = self._session.scalar(stmt)
        return float(total or 0)

    def aggregate_for_org(self, org_id: uuid.UUID) -> dict[str, float]:
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(UsageEventORM.metric, func.sum(UsageEventORM.quantity))
            .where(UsageEventORM.org_id == org_id, UsageEventORM.recorded_at >= start)
            .group_by(UsageEventORM.metric)
        )
        return {metric: float(total) for metric, total in self._session.execute(stmt).all()}
