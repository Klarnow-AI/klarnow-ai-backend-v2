"""Drop conversion_page table.

Revision ID: 035
Revises: 034
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_conversion_page_pack_id", table_name="conversion_page")
    op.drop_table("conversion_page")


def downgrade() -> None:
    op.create_table(
        "conversion_page",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("structure", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("lead_filter_type", sa.String(64), nullable=True),
        sa.Column("lead_filter_value", sa.Text(), nullable=True),
        sa.Column("proof_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_url", sa.String(2048), nullable=True),
        sa.Column("seo_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pack_id"], ["pack.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_page_pack_id", "conversion_page", ["pack_id"], unique=False)
