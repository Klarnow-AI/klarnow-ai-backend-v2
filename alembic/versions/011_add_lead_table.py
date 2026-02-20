"""Add lead table (mini CRM, pack-scoped)."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, Sequence[str], None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("budget_range", sa.String(128), nullable=True),
        sa.Column("urgency", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_pack_id", "lead", ["pack_id"], unique=False)
    op.create_index("ix_lead_status", "lead", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lead_status", "lead")
    op.drop_index("ix_lead_pack_id", "lead")
    op.drop_table("lead")
