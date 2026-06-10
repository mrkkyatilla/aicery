from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from core.domain.error_codes import ErrorCode

from gateway.adapters.db.repositories import OrgRepository, UsageRepository
from gateway.domain.tiers import TIER_LIMITS, normalize_tier


class QuotaExceededError(Exception):
    error_code = ErrorCode.QUOTA_EXCEEDED

    def __init__(self, metric: str, limit: int, used: float) -> None:
        super().__init__(f"Quota exceeded for {metric}: {used}/{limit}")
        self.metric = metric
        self.limit = limit
        self.used = used


def check_run_quota(session: Session, org_id: uuid.UUID) -> None:
    org = OrgRepository(session).get(org_id)
    tier = normalize_tier(org.tier if org else "free")
    limits = TIER_LIMITS[tier]
    usage = UsageRepository(session)
    for metric in ("agent_run", "llm_tokens_out"):
        used = usage.sum_month(org_id, metric)
        limit = limits[metric]
        if used >= limit:
            raise QuotaExceededError(metric, limit, used)
