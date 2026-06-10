"""Add runs.provider_policy JSON column (CP-1)

Revision ID: 006
Revises: 005
Create Date: 2026-05-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | Sequence[str] | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("provider_policy", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "provider_policy")
