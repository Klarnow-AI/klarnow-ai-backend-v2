"""Add name and source_code to asset for poster/flyer persistence.

Revision ID: 022
Revises: 021
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asset", sa.Column("name", sa.String(256), nullable=True))
    op.add_column("asset", sa.Column("source_code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("asset", "source_code")
    op.drop_column("asset", "name")
