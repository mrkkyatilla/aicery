"""host_workspace_root for idepus bridge integration."""

from alembic import op
import sqlalchemy as sa

revision = "011_host_workspace_root"
down_revision = "010_langgraph_checkpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("host_workspace_root", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("runs", "host_workspace_root")
