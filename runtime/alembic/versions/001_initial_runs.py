"""initial runs table

Revision ID: 001
Revises:
Create Date: 2026-05-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("workspace_id", sa.String(128), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_runs_status", "runs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_runs_status", table_name="runs")
    op.drop_table("runs")
