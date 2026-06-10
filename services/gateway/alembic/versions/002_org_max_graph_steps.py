"""org max_graph_steps policy

Revision ID: 002_org_max_graph_steps
Revises: 001_gateway_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "002_org_max_graph_steps"
down_revision = "001_gateway"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orgs", sa.Column("max_graph_steps", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("orgs", "max_graph_steps")
