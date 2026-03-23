"""Add Pack MVP fields (brand_name, USP, proof, sprint drivers, day_0_completed_at).

Revision ID: 016
Revises: 015
Create Date: Pack model MVP alignment

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, Sequence[str], None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pack", sa.Column("brand_name", sa.String(255), nullable=True))
    op.add_column("pack", sa.Column("offer_one_liner", sa.String(500), nullable=True))
    op.add_column("pack", sa.Column("target_audience", sa.String(500), nullable=True))
    op.add_column("pack", sa.Column("location_city", sa.String(128), nullable=True))
    op.add_column("pack", sa.Column("location_country", sa.String(128), nullable=True))
    op.add_column("pack", sa.Column("primary_cta", sa.String(255), nullable=True))
    op.add_column("pack", sa.Column("usp_category", sa.String(64), nullable=True))
    op.add_column("pack", sa.Column("usp_statement", sa.String(500), nullable=True))
    op.add_column("pack", sa.Column("usp_proof", sa.String(500), nullable=True))
    op.add_column("pack", sa.Column("usp_locked_line", sa.String(600), nullable=True))
    op.add_column("pack", sa.Column("proof_types", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("pack", sa.Column("proof_text", sa.Text(), nullable=True))
    op.add_column("pack", sa.Column("primary_pain", sa.String(500), nullable=True))
    op.add_column("pack", sa.Column("primary_outcome", sa.String(500), nullable=True))
    op.add_column("pack", sa.Column("hero_angle", sa.String(64), nullable=True))
    op.add_column("pack", sa.Column("business_type", sa.String(32), nullable=True))
    op.add_column("pack", sa.Column("day_0_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("pack", "day_0_completed_at")
    op.drop_column("pack", "business_type")
    op.drop_column("pack", "hero_angle")
    op.drop_column("pack", "primary_outcome")
    op.drop_column("pack", "primary_pain")
    op.drop_column("pack", "proof_text")
    op.drop_column("pack", "proof_types")
    op.drop_column("pack", "usp_locked_line")
    op.drop_column("pack", "usp_proof")
    op.drop_column("pack", "usp_statement")
    op.drop_column("pack", "usp_category")
    op.drop_column("pack", "primary_cta")
    op.drop_column("pack", "location_country")
    op.drop_column("pack", "location_city")
    op.drop_column("pack", "target_audience")
    op.drop_column("pack", "offer_one_liner")
    op.drop_column("pack", "brand_name")
