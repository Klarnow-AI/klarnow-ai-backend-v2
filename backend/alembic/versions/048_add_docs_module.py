"""Add pack-scoped Docs tables.

Revision ID: 048
Revises: 047
Create Date: 2026-03-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "048"
down_revision: Union[str, None] = "047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=True),
        sa.Column("tagline", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=512), nullable=True),
        sa.Column("services", sa.JSON(), nullable=True),
        sa.Column("team_members", sa.JSON(), nullable=True),
        sa.Column("packages", sa.JSON(), nullable=True),
        sa.Column("standard_signatory", sa.JSON(), nullable=True),
        sa.Column("standard_footer", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
        sa.Column("logo_markup", sa.Text(), nullable=True),
        sa.Column("brand_voice", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("pack_id", name="uq_company_data_pack_id"),
    )
    op.create_index("ix_company_data_pack_id", "company_data", ["pack_id"])

    op.create_table(
        "document",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linked_document_id", UUID(as_uuid=True), sa.ForeignKey("document.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("tone_preset", sa.String(length=32), nullable=False, server_default="professional"),
        sa.Column("start_mode", sa.String(length=32), nullable=False, server_default="template"),
        sa.Column("inputs_json", sa.JSON(), nullable=True),
        sa.Column("source_context_json", sa.JSON(), nullable=True),
        sa.Column("export_meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_pack_id", "document", ["pack_id"])
    op.create_index("ix_document_type", "document", ["type"])
    op.create_index("ix_document_status", "document", ["status"])
    op.create_index("ix_document_linked_document_id", "document", ["linked_document_id"])

    op.create_table(
        "document_section",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_key", sa.String(length=128), nullable=False),
        sa.Column("section_label", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_section_document_id", "document_section", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_section_document_id", table_name="document_section")
    op.drop_table("document_section")
    op.drop_index("ix_document_linked_document_id", table_name="document")
    op.drop_index("ix_document_status", table_name="document")
    op.drop_index("ix_document_type", table_name="document")
    op.drop_index("ix_document_pack_id", table_name="document")
    op.drop_table("document")
    op.drop_index("ix_company_data_pack_id", table_name="company_data")
    op.drop_table("company_data")
