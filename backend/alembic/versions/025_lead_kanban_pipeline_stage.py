"""Add pipeline_stage, due_date, deal_value, assigned_user_id to lead (Kanban).

Revision ID: 025
Revises: 024
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lead",
        sa.Column("pipeline_stage", sa.String(32), nullable=True),
    )
    op.add_column(
        "lead",
        sa.Column("due_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "lead",
        sa.Column("deal_value", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "lead",
        sa.Column(
            "assigned_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    # Backfill pipeline_stage from status
    op.execute(
        sa.text("""
            UPDATE lead
            SET pipeline_stage = CASE
                WHEN status IN ('new', 'contacted') THEN 'contacted'
                WHEN status = 'qualified' THEN 'drafting'
                WHEN status = 'converted' THEN 'closed'
                ELSE 'contacted'
            END
            WHERE pipeline_stage IS NULL
        """)
    )
    op.alter_column(
        "lead",
        "pipeline_stage",
        existing_type=sa.String(32),
        nullable=False,
        server_default="contacted",
    )
    op.create_foreign_key(
        "fk_lead_assigned_user_id_user",
        "lead",
        "user",
        ["assigned_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_lead_pipeline_stage", "lead", ["pipeline_stage"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lead_pipeline_stage", "lead")
    op.drop_constraint("fk_lead_assigned_user_id_user", "lead", type_="foreignkey")
    op.drop_column("lead", "assigned_user_id")
    op.drop_column("lead", "deal_value")
    op.drop_column("lead", "due_date")
    op.drop_column("lead", "pipeline_stage")
