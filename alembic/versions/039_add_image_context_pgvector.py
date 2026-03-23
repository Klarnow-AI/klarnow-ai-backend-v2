"""Add persistent image context tables with pgvector support.

Revision ID: 039
Revises: 038
Create Date: 2026-03-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "039"
down_revision: Union[str, Sequence[str], None] = "038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "image_context_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_storage_key", sa.String(length=1024), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("source_content_type", sa.String(length=255), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "pack_id",
            "source_type",
            "source_id",
            name="uq_image_context_item_source",
        ),
    )

    op.create_index(
        "ix_image_context_item_user_pack_status",
        "image_context_item",
        ["user_id", "pack_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_image_context_item_pack_status",
        "image_context_item",
        ["pack_id", "status"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_image_context_item_embedding_ivfflat "
        "ON image_context_item USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "image_context_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_image_context_job_status_created",
        "image_context_job",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_image_context_job_pack_status",
        "image_context_job",
        ["pack_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_image_context_job_pack_status", table_name="image_context_job")
    op.drop_index("ix_image_context_job_status_created", table_name="image_context_job")
    op.drop_table("image_context_job")

    op.execute("DROP INDEX IF EXISTS ix_image_context_item_embedding_ivfflat")
    op.drop_index("ix_image_context_item_pack_status", table_name="image_context_item")
    op.drop_index("ix_image_context_item_user_pack_status", table_name="image_context_item")
    op.drop_table("image_context_item")
