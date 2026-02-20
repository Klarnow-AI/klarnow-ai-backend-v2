"""Add sprint and day_card tables for 14-day MVP flow.

Revision ID: 015
Revises: 014
Create Date: Sprint engine

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, Sequence[str], None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sprint",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_day", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sprint_pack_id", "sprint", ["pack_id"], unique=False)

    op.create_table(
        "day_card",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sprint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("ai_output", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("user_action", sa.Text(), nullable=True),
        sa.Column("definition_of_done", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprint.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sprint_id", "day_number", name="uq_day_card_sprint_day"),
    )
    op.create_index("ix_day_card_sprint_id", "day_card", ["sprint_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_day_card_sprint_id", table_name="day_card")
    op.drop_table("day_card")
    op.drop_index("ix_sprint_pack_id", table_name="sprint")
    op.drop_table("sprint")
