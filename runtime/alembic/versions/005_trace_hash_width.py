"""Widen trace hash columns to fit sha256 hex + optional prefix

Revision ID: 005
Revises: 004
Create Date: 2026-05-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | Sequence[str] | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "trace_steps",
        "input_hash",
        existing_type=sa.String(64),
        type_=sa.String(128),
        existing_nullable=False,
    )
    op.alter_column(
        "trace_steps",
        "output_hash",
        existing_type=sa.String(64),
        type_=sa.String(128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "trace_steps",
        "output_hash",
        existing_type=sa.String(128),
        type_=sa.String(64),
        existing_nullable=True,
    )
    op.alter_column(
        "trace_steps",
        "input_hash",
        existing_type=sa.String(128),
        type_=sa.String(64),
        existing_nullable=False,
    )
