"""Add google_sub to user for Google sign-in linking.

Revision ID: 038
Revises: 037
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "038"
down_revision: Union[str, Sequence[str], None] = "037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.create_index("ix_user_google_sub", "user", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_google_sub", table_name="user")
    op.drop_column("user", "google_sub")
