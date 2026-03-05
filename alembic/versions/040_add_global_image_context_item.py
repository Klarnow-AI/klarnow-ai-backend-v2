"""Add global image context table for app-wide poster retrieval.

Revision ID: 040
Revises: 039
Create Date: 2026-03-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "040"
down_revision: Union[str, Sequence[str], None] = "039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "global_image_context_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_storage_key", sa.String(length=1024), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("source_content_type", sa.String(length=255), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_storage_key",
            name="uq_global_image_context_item_storage_key",
        ),
    )

    op.create_index(
        "ix_global_image_context_item_status",
        "global_image_context_item",
        ["status"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_global_image_context_item_embedding_ivfflat "
        "ON global_image_context_item USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_global_image_context_item_embedding_ivfflat")
    op.drop_index("ix_global_image_context_item_status", table_name="global_image_context_item")
    op.drop_table("global_image_context_item")
