"""Phase 3: conversion_page, plan_tracker, asset tables.

Revision ID: 004
Revises: 003
Create Date: Phase 3

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversion_page",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("structure", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_url", sa.String(2048), nullable=True),
        sa.Column("seo_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_page_pack_id", "conversion_page", ["pack_id"], unique=False)

    op.create_table(
        "plan_tracker",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon", sa.String(16), nullable=False),
        sa.Column("plan_content", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("unlock_schedule", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("daily_status", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("weekly_checkpoint", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_tracker_pack_id", "plan_tracker", ["pack_id"], unique=False)

    op.create_table(
        "asset",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("version", sa.String(16), nullable=True),
        sa.Column("template_id", sa.String(128), nullable=True),
        sa.Column("output_key", sa.String(512), nullable=True),
        sa.Column("script", sa.String(8000), nullable=True),
        sa.Column("srt_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_pack_id", "asset", ["pack_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_asset_pack_id", "asset")
    op.drop_table("asset")
    op.drop_index("ix_plan_tracker_pack_id", "plan_tracker")
    op.drop_table("plan_tracker")
    op.drop_index("ix_conversion_page_pack_id", "conversion_page")
    op.drop_table("conversion_page")
