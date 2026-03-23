"""Add ad_factory_render table.

Revision ID: 033
Revises: 032
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ad_factory_render",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("brand_brief_snapshot", JSONB, nullable=False),
        sa.Column("pack_snapshot", JSONB, nullable=False),
        sa.Column("selection_seed", sa.String(128), nullable=False),
        sa.Column("pattern_ids_used", JSONB, nullable=True),
        sa.Column("hook_ids_used", JSONB, nullable=True),
        sa.Column("proof_strategy_id", sa.String(64), nullable=True),
        sa.Column("cta_id", sa.String(64), nullable=True),
        sa.Column("engines_output", JSONB, nullable=False),
        sa.Column("variants", JSONB, nullable=False),
        sa.Column("render_metadata", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_ad_factory_render_pack_id", "ad_factory_render", ["pack_id"])


def downgrade() -> None:
    op.drop_index("ix_ad_factory_render_pack_id", table_name="ad_factory_render")
    op.drop_table("ad_factory_render")
