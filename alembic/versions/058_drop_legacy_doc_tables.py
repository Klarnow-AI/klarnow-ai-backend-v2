"""Drop legacy document, document_section, and company_data tables.

Revision ID: 058
Revises: 057
Create Date: 2026-04-10

These tables belonged to the removed docs module (proposals/invoices/company profiles).
"""

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


def upgrade() -> None:
    op.drop_table("document_section")
    op.drop_table("document")
    op.drop_table("company_data")


def downgrade() -> None:
    # Recreate in reverse order to satisfy FK constraints
    op.create_table(
        "company_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("business_name", sa.String(255), nullable=True),
        sa.Column("tagline", sa.String(500), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("services", JSON, nullable=True),
        sa.Column("team_members", JSON, nullable=True),
        sa.Column("packages", JSON, nullable=True),
        sa.Column("standard_signatory", JSON, nullable=True),
        sa.Column("standard_footer", sa.Text, nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("logo_markup", sa.Text, nullable=True),
        sa.Column("brand_voice", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pack_id", UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linked_document_id", UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("tone_preset", sa.String(32), nullable=True, server_default="professional"),
        sa.Column("start_mode", sa.String(32), nullable=True, server_default="template"),
        sa.Column("inputs_json", JSON, nullable=True),
        sa.Column("source_context_json", JSON, nullable=True),
        sa.Column("export_meta_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document_section",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_key", sa.String(128), nullable=True),
        sa.Column("section_label", sa.String(255), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("order_index", sa.Integer, nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
