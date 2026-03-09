"""Remove obsolete subscription table.

Revision ID: 045
Revises: 044
Create Date: 2026-03-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "045"
down_revision: Union[str, None] = "044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "subscription" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("subscription")}
    if "ix_subscription_user_id" in indexes:
        op.drop_index("ix_subscription_user_id", table_name="subscription")
    op.drop_table("subscription")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "subscription" in inspector.get_table_names():
        return

    op.create_table(
        "subscription",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="free"),
        sa.Column("credits_remaining", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credits_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cycle_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cycle_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_subscription_user_id", "subscription", ["user_id"], unique=True)
