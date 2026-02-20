"""Add pack_type to pack table.

Revision ID: 008
Revises: 007
Create Date: Pack type for MVP routing (enquiries, quotes, sales)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pack",
        sa.Column("pack_type", sa.String(32), nullable=False, server_default="enquiries"),
    )


def downgrade() -> None:
    op.drop_column("pack", "pack_type")
