"""Drop plan_tracker and weekly_checkin tables (legacy 7/30/90 plan tracker removed).

Revision ID: 020
Revises: 019
Create Date: 2026-02-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop weekly_checkin first (FK to plan_tracker)
    op.drop_index("ix_weekly_checkin_pack_id", "weekly_checkin")
    op.drop_index("ix_weekly_checkin_plan_tracker_id", "weekly_checkin")
    op.drop_table("weekly_checkin")

    op.drop_index("ix_plan_tracker_pack_id", "plan_tracker")
    op.drop_table("plan_tracker")


def downgrade() -> None:
    # Recreate plan_tracker first (weekly_checkin references it)
    op.create_table(
        "plan_tracker",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon", sa.String(16), nullable=False),
        sa.Column("plan_content", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("unlock_schedule", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("daily_status", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("weekly_checkpoint", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_tracker_pack_id", "plan_tracker", ["pack_id"], unique=False)

    op.create_table(
        "weekly_checkin",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_tracker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("what_worked", sa.Text(), nullable=True),
        sa.Column("what_did_not", sa.Text(), nullable=True),
        sa.Column("new_proof", sa.Text(), nullable=True),
        sa.Column("offer_tweak", sa.Text(), nullable=True),
        sa.Column("next_goal", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_tracker_id"], ["plan_tracker.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weekly_checkin_plan_tracker_id", "weekly_checkin", ["plan_tracker_id"], unique=False)
    op.create_index("ix_weekly_checkin_pack_id", "weekly_checkin", ["pack_id"], unique=False)
