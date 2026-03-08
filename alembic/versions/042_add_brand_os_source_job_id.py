"""Add Brand OS source job id for onboarding worker idempotency.

Revision ID: 042
Revises: 041
Create Date: 2026-03-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "042"
down_revision: Union[str, Sequence[str], None] = "041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("brand_os", sa.Column("source_job_id", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_brand_os_source_job_id",
        "brand_os",
        ["source_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_brand_os_source_job_id", table_name="brand_os")
    op.drop_column("brand_os", "source_job_id")
