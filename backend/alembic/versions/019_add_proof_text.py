"""Add proof_text to proof for generated proof fallback

Revision ID: 019
Revises: 018
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("proof", sa.Column("proof_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("proof", "proof_text")
