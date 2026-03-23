"""Add channel, template_key to followup_task; last_contacted_at to lead.

Revision ID: 030
Revises: 029
Create Date: 2026-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "followup_task",
        sa.Column("template_key", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "followup_task",
        sa.Column("channel", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "lead",
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("followup_task", "channel")
    op.drop_column("followup_task", "template_key")
    op.drop_column("lead", "last_contacted_at")
