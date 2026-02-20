"""Drop legacy brand_os columns (mission, vision, values, positioning, personas, voice_and_messaging).

Revision ID: 014
Revises: 013
Create Date: Brand OS schema alignment (post backfill)

"""
from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, Sequence[str], None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("brand_os", "voice_and_messaging")
    op.drop_column("brand_os", "personas")
    op.drop_column("brand_os", "positioning")
    op.drop_column("brand_os", "values")
    op.drop_column("brand_os", "vision")
    op.drop_column("brand_os", "mission")


def downgrade() -> None:
    from sqlalchemy import sa
    from sqlalchemy.dialects import postgresql

    op.add_column(
        "brand_os",
        sa.Column("mission", sa.String(2000), nullable=True),
    )
    op.add_column(
        "brand_os",
        sa.Column("vision", sa.String(2000), nullable=True),
    )
    op.add_column(
        "brand_os",
        sa.Column("values", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "brand_os",
        sa.Column("positioning", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "brand_os",
        sa.Column("personas", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "brand_os",
        sa.Column("voice_and_messaging", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
