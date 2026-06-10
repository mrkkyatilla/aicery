"""Add pipeline_id to runs

Revision ID: 003
Revises: 002
"""

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("pipeline_id", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "pipeline_id")
