"""Stripe Connect (user) and Invoice Stripe fields.

Revision ID: 026
Revises: 025
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User: Stripe Connect
    op.add_column(
        "user",
        sa.Column("stripe_connect_account_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("stripe_connect_onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_user_stripe_connect_account_id", "user", ["stripe_connect_account_id"], unique=False)

    # Invoice: Stripe invoice id and hosted URL
    op.add_column(
        "invoice",
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "invoice",
        sa.Column("stripe_hosted_url", sa.String(2048), nullable=True),
    )
    op.create_index("ix_invoice_stripe_invoice_id", "invoice", ["stripe_invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invoice_stripe_invoice_id", "invoice")
    op.drop_column("invoice", "stripe_hosted_url")
    op.drop_column("invoice", "stripe_invoice_id")
    op.drop_index("ix_user_stripe_connect_account_id", "user")
    op.drop_column("user", "stripe_connect_onboarding_complete")
    op.drop_column("user", "stripe_connect_account_id")
