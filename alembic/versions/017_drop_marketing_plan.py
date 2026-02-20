"""Drop marketing_plan table and pack.active_marketing_plan_id.

Revision ID: 017
Revises: 016
Create Date: Remove marketing plan module

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, Sequence[str], None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_pack_active_marketing_plan", "pack", type_="foreignkey")
    op.drop_column("pack", "active_marketing_plan_id")
    op.drop_index("ix_marketing_plan_pack_id", "marketing_plan")
    op.drop_table("marketing_plan")


def downgrade() -> None:
    op.create_table(
        "marketing_plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("plan_type", sa.String(32), nullable=False),
        sa.Column("content", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_plan_pack_id", "marketing_plan", ["pack_id"], unique=False)
    op.add_column("pack", sa.Column("active_marketing_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_pack_active_marketing_plan",
        "pack", "marketing_plan",
        ["active_marketing_plan_id"], ["id"],
        ondelete="SET NULL",
    )
