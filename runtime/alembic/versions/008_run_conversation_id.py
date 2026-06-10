"""Add runs.conversation_id (MEM-P2.1)

Revision ID: 008
Revises: 007
Create Date: 2026-05-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | Sequence[str] | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("conversation_id", sa.String(length=128), nullable=True))
    op.create_index("ix_runs_conversation_id", "runs", ["conversation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_runs_conversation_id", table_name="runs")
    op.drop_column("runs", "conversation_id")
