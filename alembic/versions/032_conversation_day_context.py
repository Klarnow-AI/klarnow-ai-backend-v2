"""Add day_context to conversation for Day 0-3 flow.

Revision ID: 032
Revises: 031
Create Date: 2026-02-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation",
        sa.Column("day_context", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation", "day_context")
