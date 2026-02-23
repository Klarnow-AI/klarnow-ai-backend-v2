"""Add subdomain_slug to builder_project for subdomain-based site URLs.

Revision ID: 027
Revises: 026
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "builder_project",
        sa.Column("subdomain_slug", sa.String(63), nullable=True),
    )
    op.create_index(
        op.f("ix_builder_project_subdomain_slug"),
        "builder_project",
        ["subdomain_slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_builder_project_subdomain_slug"), table_name="builder_project")
    op.drop_column("builder_project", "subdomain_slug")
