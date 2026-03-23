"""Add decision_log table for Phase 2.

Revision ID: 003
Revises: 002
Create Date: Phase 2

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inputs_sanitized", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_log_pack_id", "decision_log", ["pack_id"], unique=False)
    op.create_index("ix_decision_log_tool_name", "decision_log", ["tool_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_decision_log_tool_name", "decision_log")
    op.drop_index("ix_decision_log_pack_id", "decision_log")
    op.drop_table("decision_log")
