from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from core.domain.hitl import ApprovalDecision
from core.domain.run import RunStatus
from runtime.adapters.db.approval_repository import ApprovalRepository
from runtime.adapters.db.repository import RunRepository
from runtime.config import Settings
from runtime.services.hitl_service import HitlService

logger = logging.getLogger(__name__)


def sweep_expired_hitl_once(session_factory) -> int:
    """Reject expired open approvals and fail suspended runs."""
    settings = Settings()
    if not settings.hitl_enabled or not settings.hitl_sweeper_enabled:
        return 0

    session = session_factory()
    processed = 0
    try:
        now = datetime.now(UTC)
        repo = ApprovalRepository(session)
        run_repo = RunRepository(session)
        hitl = HitlService(session, settings=settings)
        for pending in repo.list_expired_open(now):
            run = run_repo.get(pending.run_id)
            if run is None:
                hitl.resolve(pending.approval_id, decision=ApprovalDecision.REJECT)
                processed += 1
                continue
            hitl.apply_timeout_policy(run, pending)
            if run.status in (RunStatus.SUSPENDED, RunStatus.RUNNING):
                run.status = RunStatus.FAILED
                run.error_code = "HITL_REJECTED"
                run.error_message = "Human approval timed out"
                run.updated_at = datetime.now(UTC)
                run_repo.update(run)
                processed += 1
        return processed
    finally:
        session.close()


async def run_hitl_sweeper_loop(session_factory, *, settings: Settings | None = None) -> None:
    settings = settings or Settings()
    interval = max(1, settings.hitl_sweeper_interval_sec)
    while True:
        try:
            count = await asyncio.to_thread(sweep_expired_hitl_once, session_factory)
            if count:
                logger.info("hitl.sweeper", extra={"expired_rejected": count})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("hitl.sweeper failed")
        await asyncio.sleep(interval)
