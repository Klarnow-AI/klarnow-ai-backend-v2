"""Update waitlist signup fields.

Revision ID: 050
Revises: 049
Create Date: 2026-03-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "050"
down_revision: Union[str, None] = "049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "waitlist_signup",
        "name",
        new_column_name="first_name",
        existing_type=sa.String(length=255),
        existing_nullable=True,
    )
    op.add_column(
        "waitlist_signup",
        sa.Column("role", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "waitlist_signup",
        sa.Column("goal", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("waitlist_signup", "goal")
    op.drop_column("waitlist_signup", "role")
    op.alter_column(
        "waitlist_signup",
        "first_name",
        new_column_name="name",
        existing_type=sa.String(length=255),
        existing_nullable=True,
    )
