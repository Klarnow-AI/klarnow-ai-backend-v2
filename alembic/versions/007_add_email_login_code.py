"""Add email_login_code table for magic link / code sign-in.

Revision ID: 007
Revises: 006
Create Date: Email sign-in code

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_login_code",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_login_code_email",
        "email_login_code",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_email_login_code_email", "email_login_code")
    op.drop_table("email_login_code")
