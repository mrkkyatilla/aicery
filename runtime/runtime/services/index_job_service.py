from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from runtime.adapters.db.models import IndexJobORM
from runtime.adapters.db.session import get_session_factory
from runtime.config import Settings
from runtime.intelligence.indexer import IndexResult, index_workspace

logger = logging.getLogger(__name__)


class IndexJobStatus(BaseModel):
    job_id: str
    status: str
    workspace_id: str
    paths: list[str]
    result: IndexResult | None = None
    error_message: str | None = None


class IndexJobService:
    def __init__(self) -> None:
        self._factory = get_session_factory()
        self._running: set[uuid.UUID] = set()

    def enqueue_index(
        self,
        workspace_id: str,
        paths: list[str],
        *,
        workspace_root: str | None = None,
    ) -> str:
        job_id = uuid.uuid4()
        now = datetime.now(UTC)
        with self._session() as session:
            session.add(
                IndexJobORM(
                    id=job_id,
                    workspace_id=workspace_id,
                    paths=paths,
                    status="pending",
                    created_at=now,
                )
            )
            session.commit()
        asyncio.create_task(self._run_job(job_id, workspace_id, paths, workspace_root=workspace_root))
        return str(job_id)

    async def get_job(self, job_id: str) -> IndexJobStatus | None:
        try:
            uid = uuid.UUID(job_id)
        except ValueError:
            return None
        with self._session() as session:
            row = session.get(IndexJobORM, uid)
            if row is None:
                return None
            result = None
            if row.result_json:
                result = IndexResult.model_validate(row.result_json)
            return IndexJobStatus(
                job_id=str(row.id),
                status=row.status,
                workspace_id=row.workspace_id,
                paths=list(row.paths),
                result=result,
                error_message=row.error_message,
            )

    def _session(self) -> Session:
        return self._factory()

    async def _run_job(
        self,
        job_id: uuid.UUID,
        workspace_id: str,
        paths: list[str],
        *,
        workspace_root: str | None,
    ) -> None:
        if job_id in self._running:
            return
        self._running.add(job_id)
        self._update_status(job_id, "running")
        try:
            result = await index_workspace(workspace_id, paths, workspace_root=workspace_root)
            self._complete(job_id, result)
        except Exception as exc:
            logger.exception("Index job %s failed", job_id)
            self._fail(job_id, str(exc))
        finally:
            self._running.discard(job_id)

    def _update_status(self, job_id: uuid.UUID, status: str) -> None:
        with self._session() as session:
            row = session.get(IndexJobORM, job_id)
            if row is None:
                return
            row.status = status
            session.commit()

    def _complete(self, job_id: uuid.UUID, result: IndexResult) -> None:
        with self._session() as session:
            row = session.get(IndexJobORM, job_id)
            if row is None:
                return
            row.status = "completed"
            row.result_json = result.model_dump()
            row.completed_at = datetime.now(UTC)
            session.commit()

    def _fail(self, job_id: uuid.UUID, message: str) -> None:
        with self._session() as session:
            row = session.get(IndexJobORM, job_id)
            if row is None:
                return
            row.status = "failed"
            row.error_message = message
            row.completed_at = datetime.now(UTC)
            session.commit()


_service: IndexJobService | None = None


def get_index_job_service() -> IndexJobService:
    global _service
    if _service is None:
        _service = IndexJobService()
    return _service


def should_enqueue_async(paths: list[str], *, async_requested: bool) -> bool:
    settings = Settings()
    if async_requested:
        return True
    return len(paths) >= settings.index_async_path_threshold
