"""Phase 1: brand_os, marketing_plan, campaign tables and pack columns.

Revision ID: 002
Revises: 001
Create Date: Phase 1

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_os",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("mission", sa.String(2000), nullable=True),
        sa.Column("vision", sa.String(2000), nullable=True),
        sa.Column("values", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("positioning", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("personas", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("voice_and_messaging", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brand_os_pack_id", "brand_os", ["pack_id"], unique=False)

    op.create_table(
        "marketing_plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("plan_type", sa.String(32), nullable=False),
        sa.Column("content", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_plan_pack_id", "marketing_plan", ["pack_id"], unique=False)

    op.create_table(
        "campaign",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("primary_cta", sa.String(255), nullable=True),
        sa.Column("goal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("angles", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("active_angle_id", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_pack_id", "campaign", ["pack_id"], unique=False)

    op.add_column("pack", sa.Column("onboarding_answers", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("pack", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pack", sa.Column("active_brand_os_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pack", sa.Column("active_marketing_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pack", sa.Column("active_campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_pack_active_brand_os",
        "pack", "brand_os",
        ["active_brand_os_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pack_active_marketing_plan",
        "pack", "marketing_plan",
        ["active_marketing_plan_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_pack_active_campaign",
        "pack", "campaign",
        ["active_campaign_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_pack_active_campaign", "pack", type_="foreignkey")
    op.drop_constraint("fk_pack_active_marketing_plan", "pack", type_="foreignkey")
    op.drop_constraint("fk_pack_active_brand_os", "pack", type_="foreignkey")
    op.drop_column("pack", "active_campaign_id")
    op.drop_column("pack", "active_marketing_plan_id")
    op.drop_column("pack", "active_brand_os_id")
    op.drop_column("pack", "onboarding_completed_at")
    op.drop_column("pack", "onboarding_answers")

    op.drop_index("ix_campaign_pack_id", "campaign")
    op.drop_table("campaign")
    op.drop_index("ix_marketing_plan_pack_id", "marketing_plan")
    op.drop_table("marketing_plan")
    op.drop_index("ix_brand_os_pack_id", "brand_os")
    op.drop_table("brand_os")
