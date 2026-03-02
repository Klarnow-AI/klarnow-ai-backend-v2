"""Add published_files to builder_project for revert-to-published.

Revision ID: 034
Revises: 033
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "builder_project",
        sa.Column("published_files", JSON, nullable=True),
    )
    # Backfill: set published_files = files for already-published projects
    op.execute("""
        UPDATE builder_project
        SET published_files = files
        WHERE published_at IS NOT NULL AND published_files IS NULL
    """)


def downgrade() -> None:
    op.drop_column("builder_project", "published_files")
