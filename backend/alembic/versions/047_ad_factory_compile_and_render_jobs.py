"""Add Ad Factory compile and render job tables.

Revision ID: 047
Revises: 046
Create Date: 2026-03-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "047"
down_revision: Union[str, None] = "046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ad_factory_compile",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="compiled"),
        sa.Column("brand_brief_snapshot", JSONB, nullable=False),
        sa.Column("pack_snapshot", JSONB, nullable=False),
        sa.Column("selection", JSONB, nullable=False),
        sa.Column("versions", JSONB, nullable=False),
        sa.Column("compile_result", JSONB, nullable=False),
        sa.Column("claim_guard_result", JSONB, nullable=False),
        sa.Column("validator_result", JSONB, nullable=False),
        sa.Column("launch_recommendation", JSONB, nullable=False),
        sa.Column("launch_state", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ad_factory_compile_pack_id", "ad_factory_compile", ["pack_id"])

    op.create_table(
        "ad_factory_render_job",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "compile_result_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_factory_compile.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("selected_variants", JSONB, nullable=False),
        sa.Column("durations_requested", JSONB, nullable=False),
        sa.Column("voiceover_addon", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_target", sa.String(length=32), nullable=False, server_default="kling"),
        sa.Column("provider_adapter_version", sa.String(length=64), nullable=False),
        sa.Column("billing_snapshot", JSONB, nullable=False),
        sa.Column("provider_job_ids", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("asset_urls", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("retry_state", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("failure_state", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("render_result", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ad_factory_render_job_compile_result_id", "ad_factory_render_job", ["compile_result_id"])
    op.create_index("ix_ad_factory_render_job_pack_id", "ad_factory_render_job", ["pack_id"])
    op.create_index("ix_ad_factory_render_job_idempotency_key", "ad_factory_render_job", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_ad_factory_render_job_idempotency_key", table_name="ad_factory_render_job")
    op.drop_index("ix_ad_factory_render_job_pack_id", table_name="ad_factory_render_job")
    op.drop_index("ix_ad_factory_render_job_compile_result_id", table_name="ad_factory_render_job")
    op.drop_table("ad_factory_render_job")
    op.drop_index("ix_ad_factory_compile_pack_id", table_name="ad_factory_compile")
    op.drop_table("ad_factory_compile")
