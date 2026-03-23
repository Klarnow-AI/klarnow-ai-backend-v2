"""Add password_reset_token table for forgot/reset password flow.

Revision ID: 028
Revises: 027
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_token",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_token_email",
        "password_reset_token",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_token_token",
        "password_reset_token",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_token_token", "password_reset_token")
    op.drop_index("ix_password_reset_token_email", "password_reset_token")
    op.drop_table("password_reset_token")
