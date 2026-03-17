"""Add operations module tables.

Revision ID: 051
Revises: 050
Create Date: 2026-03-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "051"
down_revision: Union[str, None] = "050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pack_operating_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_type", sa.String(length=64), nullable=True),
        sa.Column("services_offers", sa.JSON(), nullable=True),
        sa.Column("pricing", sa.JSON(), nullable=True),
        sa.Column("booking_rules", sa.JSON(), nullable=True),
        sa.Column("working_hours", sa.JSON(), nullable=True),
        sa.Column("contact_preferences", sa.JSON(), nullable=True),
        sa.Column("service_area", sa.JSON(), nullable=True),
        sa.Column("automation_settings", sa.JSON(), nullable=True),
        sa.Column("approval_settings", sa.JSON(), nullable=True),
        sa.Column("business_rules", sa.JSON(), nullable=True),
        sa.Column("tone_guidance", sa.Text(), nullable=True),
        sa.Column("business_notes", sa.Text(), nullable=True),
        sa.Column("timezone_name", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("pack_id", name="uq_pack_operating_profile_pack_id"),
    )
    op.create_index(
        "ix_pack_operating_profile_pack_id",
        "pack_operating_profile",
        ["pack_id"],
        unique=True,
    )

    op.create_table(
        "operating_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_contact", sa.String(length=255), nullable=True),
        sa.Column("customer_stage", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("commercial_sensitivity", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("response_mode", sa.String(length=64), nullable=False),
        sa.Column("action_mode", sa.String(length=64), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("suggested_reply", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.JSON(), nullable=True),
        sa.Column("detected_reason", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_operating_activity_pack_id", "operating_activity", ["pack_id"], unique=False)
    op.create_index("ix_operating_activity_source_ref", "operating_activity", ["source_ref"], unique=False)
    op.create_index("ix_operating_activity_activity_type", "operating_activity", ["activity_type"], unique=False)
    op.create_index("ix_operating_activity_priority", "operating_activity", ["priority"], unique=False)
    op.create_index("ix_operating_activity_status", "operating_activity", ["status"], unique=False)

    op.create_table(
        "approval_request",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operating_activity.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_response", sa.Text(), nullable=True),
        sa.Column("proposed_action", sa.JSON(), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=True),
        sa.Column("final_action", sa.JSON(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_request_pack_id", "approval_request", ["pack_id"], unique=False)
    op.create_index("ix_approval_request_activity_id", "approval_request", ["activity_id"], unique=False)
    op.create_index("ix_approval_request_status", "approval_request", ["status"], unique=False)

    op.create_table(
        "action_log_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operating_activity.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approval_request.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("execution_mode", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("provider_ref", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_action_log_entry_pack_id", "action_log_entry", ["pack_id"], unique=False)
    op.create_index("ix_action_log_entry_activity_id", "action_log_entry", ["activity_id"], unique=False)
    op.create_index("ix_action_log_entry_approval_request_id", "action_log_entry", ["approval_request_id"], unique=False)
    op.create_index("ix_action_log_entry_status", "action_log_entry", ["status"], unique=False)

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pack.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operating_activity.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approval_request.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("scenario_key", sa.String(length=255), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("final_content", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendation_feedback_pack_id", "recommendation_feedback", ["pack_id"], unique=False)
    op.create_index("ix_recommendation_feedback_activity_id", "recommendation_feedback", ["activity_id"], unique=False)
    op.create_index("ix_recommendation_feedback_approval_request_id", "recommendation_feedback", ["approval_request_id"], unique=False)
    op.create_index("ix_recommendation_feedback_scenario_key", "recommendation_feedback", ["scenario_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_recommendation_feedback_scenario_key", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_approval_request_id", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_activity_id", table_name="recommendation_feedback")
    op.drop_index("ix_recommendation_feedback_pack_id", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")

    op.drop_index("ix_action_log_entry_status", table_name="action_log_entry")
    op.drop_index("ix_action_log_entry_approval_request_id", table_name="action_log_entry")
    op.drop_index("ix_action_log_entry_activity_id", table_name="action_log_entry")
    op.drop_index("ix_action_log_entry_pack_id", table_name="action_log_entry")
    op.drop_table("action_log_entry")

    op.drop_index("ix_approval_request_status", table_name="approval_request")
    op.drop_index("ix_approval_request_activity_id", table_name="approval_request")
    op.drop_index("ix_approval_request_pack_id", table_name="approval_request")
    op.drop_table("approval_request")

    op.drop_index("ix_operating_activity_status", table_name="operating_activity")
    op.drop_index("ix_operating_activity_priority", table_name="operating_activity")
    op.drop_index("ix_operating_activity_activity_type", table_name="operating_activity")
    op.drop_index("ix_operating_activity_source_ref", table_name="operating_activity")
    op.drop_index("ix_operating_activity_pack_id", table_name="operating_activity")
    op.drop_table("operating_activity")

    op.drop_index("ix_pack_operating_profile_pack_id", table_name="pack_operating_profile")
    op.drop_table("pack_operating_profile")
