import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.domain.provider_policy import policy_from_dict, policy_to_dict
from core.domain.run import Run, RunCreate, RunStatus
from runtime.adapters.db.models import RunORM


def _to_domain(row: RunORM) -> Run:
    return Run(
        id=str(row.id),
        status=RunStatus(row.status),
        agent_id=row.agent_id,
        input_text=row.input_text,
        workspace_id=row.workspace_id,
        pipeline_id=row.pipeline_id,
        conversation_id=row.conversation_id,
        provider_policy=policy_from_dict(row.provider_policy),
        output_text=row.output_text,
        created_at=row.created_at,
        updated_at=row.updated_at,
        error_code=row.error_code,
        error_message=row.error_message,
    )


def _to_orm(run: Run) -> RunORM:
    return RunORM(
        id=uuid.UUID(run.id),
        status=run.status.value,
        agent_id=run.agent_id,
        input_text=run.input_text,
        workspace_id=run.workspace_id,
        pipeline_id=run.pipeline_id,
        conversation_id=run.conversation_id,
        provider_policy=policy_to_dict(run.provider_policy),
        output_text=run.output_text,
        error_code=run.error_code,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


class RunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: RunCreate) -> Run:
        now = datetime.now(UTC)
        run = Run(
            agent_id=data.agent_id,
            input_text=data.input_text,
            workspace_id=data.workspace_id,
            pipeline_id=data.pipeline_id,
            conversation_id=data.conversation_id,
            provider_policy=data.provider_policy,
            status=RunStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        if run.conversation_id is None:
            run.conversation_id = run.id
        row = _to_orm(run)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def get(self, run_id: str) -> Run | None:
        row = self._session.get(RunORM, uuid.UUID(run_id))
        if row is None:
            return None
        self._session.refresh(row)
        return _to_domain(row)

    def update(self, run: Run) -> Run:
        row = self._session.get(RunORM, uuid.UUID(run.id))
        if row is None:
            raise ValueError(f"Run not found: {run.id}")
        row.status = run.status.value
        row.agent_id = run.agent_id
        row.input_text = run.input_text
        row.workspace_id = run.workspace_id
        row.pipeline_id = run.pipeline_id
        row.conversation_id = run.conversation_id
        row.provider_policy = policy_to_dict(run.provider_policy)
        row.output_text = run.output_text
        row.error_code = run.error_code
        row.error_message = run.error_message
        row.updated_at = run.updated_at
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)
