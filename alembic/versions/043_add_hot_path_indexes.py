"""Add composite indexes for DB hot paths.

Revision ID: 043
Revises: 042
Create Date: 2026-03-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "043"
down_revision: Union[str, Sequence[str], None] = "042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_pack_created_by_user_status_created_at",
        "pack",
        ["created_by_user_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_lead_pack_id_status_created_at",
        "lead",
        ["pack_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_proposal_pack_id_status_created_at",
        "proposal",
        ["pack_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_invoice_pack_id_status_created_at",
        "invoice",
        ["pack_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_brand_os_pack_id_is_active",
        "brand_os",
        ["pack_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_pack_id_is_active",
        "campaign",
        ["pack_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_sprint_pack_id_status",
        "sprint",
        ["pack_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sprint_pack_id_status", table_name="sprint")
    op.drop_index("ix_campaign_pack_id_is_active", table_name="campaign")
    op.drop_index("ix_brand_os_pack_id_is_active", table_name="brand_os")
    op.drop_index("ix_invoice_pack_id_status_created_at", table_name="invoice")
    op.drop_index("ix_proposal_pack_id_status_created_at", table_name="proposal")
    op.drop_index("ix_lead_pack_id_status_created_at", table_name="lead")
    op.drop_index("ix_pack_created_by_user_status_created_at", table_name="pack")
