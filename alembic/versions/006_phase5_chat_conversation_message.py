"""Phase 5: conversation and message tables for Chat with Klaro.

Revision ID: 006
Revises: 005
Create Date: Phase 5

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_user_id", "conversation", ["user_id"], unique=False)
    op.create_index("ix_conversation_pack_id", "conversation", ["pack_id"], unique=False)

    op.create_table(
        "message",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tool_calls", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("tool_results", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_preview", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_conversation_id", "message", ["conversation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_message_conversation_id", "message")
    op.drop_table("message")
    op.drop_index("ix_conversation_pack_id", "conversation")
    op.drop_index("ix_conversation_user_id", "conversation")
    op.drop_table("conversation")
