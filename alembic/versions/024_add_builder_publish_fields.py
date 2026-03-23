"""Add live_url and published_at to builder_project.

Revision ID: 024
Revises: 023
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("builder_project", sa.Column("live_url", sa.Text(), nullable=True))
    op.add_column(
        "builder_project",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("builder_project", "published_at")
    op.drop_column("builder_project", "live_url")
