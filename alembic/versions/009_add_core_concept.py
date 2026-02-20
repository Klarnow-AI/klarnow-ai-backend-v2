"""Add core_concept to pack table.

Revision ID: 009
Revises: 008
Create Date: Core concept lock (one sentence) after onboarding

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, Sequence[str], None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pack",
        sa.Column("core_concept", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pack", "core_concept")
