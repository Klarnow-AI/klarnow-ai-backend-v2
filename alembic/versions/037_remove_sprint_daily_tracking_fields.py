"""Remove sprint day tracking fields from day_card.

Revision ID: 037
Revises: 036
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "037"
down_revision: Union[str, Sequence[str], None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("day_card", "output_shipped")
    op.drop_column("day_card", "proof_logged")
    op.drop_column("day_card", "followup_count")
    op.drop_column("day_card", "outreach_count")


def downgrade() -> None:
    op.add_column(
        "day_card",
        sa.Column("outreach_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "day_card",
        sa.Column("followup_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "day_card",
        sa.Column("proof_logged", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "day_card",
        sa.Column("output_shipped", sa.Boolean(), nullable=False, server_default="false"),
    )
