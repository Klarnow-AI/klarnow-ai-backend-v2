"""Add composite index on message(conversation_id, created_at).

Revision ID: 053
Revises: 052
Create Date: 2026-03-23
"""

from typing import Sequence, Union

from alembic import op


revision: str = "053"
down_revision: Union[str, None] = "052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_messages_conv_created",
        "message",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_messages_conv_created", table_name="message")
