"""Enforce one campaign per pack via unique constraint on campaign.pack_id.

Revision ID: 054
Revises: 053
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op


revision: str = "054"
down_revision: Union[str, None] = "053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate campaigns per pack, keeping only the most recently active one
    # (or the most recent by created_at if none are active).
    op.execute("""
        DELETE FROM campaign
        WHERE id NOT IN (
            SELECT DISTINCT ON (pack_id) id
            FROM campaign
            ORDER BY pack_id, is_active DESC, created_at DESC
        )
    """)
    op.create_unique_constraint("uq_campaign_pack_id", "campaign", ["pack_id"])


def downgrade() -> None:
    op.drop_constraint("uq_campaign_pack_id", "campaign", type_="unique")
