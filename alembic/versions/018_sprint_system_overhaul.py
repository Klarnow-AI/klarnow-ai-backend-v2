"""Sprint system overhaul with modes, tracking, subscriptions, tasks, response rules

Revision ID: 018_sprint_system_overhaul
Revises: 017_drop_marketing_plan
Create Date: 2026-02-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscription table
    op.create_table(
        'subscription',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan', sa.String(length=32), nullable=False, server_default='free'),
        sa.Column('credits_remaining', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('credits_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cycle_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cycle_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_subscription_user_id'), 'subscription', ['user_id'], unique=True)

    # Create followup_task table
    op.create_table(
        'followup_task',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pack_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_type', sa.String(length=64), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pack_id'], ['pack.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['lead.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_followup_task_pack_id'), 'followup_task', ['pack_id'], unique=False)
    op.create_index(op.f('ix_followup_task_status'), 'followup_task', ['status'], unique=False)

    # Create response_rule table
    op.create_table(
        'response_rule',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pack_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trigger', sa.String(length=64), nullable=False),
        sa.Column('response_template', sa.Text(), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pack_id'], ['pack.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_response_rule_pack_id'), 'response_rule', ['pack_id'], unique=False)

    # Add new fields to sprint table
    op.add_column('sprint', sa.Column('mode', sa.String(length=32), nullable=False, server_default='build'))
    op.add_column('sprint', sa.Column('success_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # Add new tracking fields to day_card table
    op.add_column('day_card', sa.Column('outreach_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_card', sa.Column('followup_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('day_card', sa.Column('proof_logged', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('day_card', sa.Column('output_shipped', sa.Boolean(), nullable=False, server_default='false'))

    # Add new fields to pack table
    op.add_column('pack', sa.Column('website_url', sa.String(length=512), nullable=True))
    op.add_column('pack', sa.Column('has_existing_customers', sa.Boolean(), nullable=True))

    # Add lead filter fields to conversion_page table
    op.add_column('conversion_page', sa.Column('lead_filter_type', sa.String(length=64), nullable=True))
    op.add_column('conversion_page', sa.Column('lead_filter_value', sa.Text(), nullable=True))
    op.add_column('conversion_page', sa.Column('proof_ids', postgresql.ARRAY(sa.String()), nullable=True))

    # Create free subscriptions for all existing users
    op.execute("""
        INSERT INTO subscription (id, user_id, plan, credits_remaining, credits_total, status)
        SELECT gen_random_uuid(), id, 'free', 0, 0, 'active'
        FROM "user"
        WHERE id NOT IN (SELECT user_id FROM subscription)
    """)


def downgrade() -> None:
    # Remove fields from conversion_page
    op.drop_column('conversion_page', 'proof_ids')
    op.drop_column('conversion_page', 'lead_filter_value')
    op.drop_column('conversion_page', 'lead_filter_type')

    # Remove fields from pack
    op.drop_column('pack', 'has_existing_customers')
    op.drop_column('pack', 'website_url')

    # Remove fields from day_card
    op.drop_column('day_card', 'output_shipped')
    op.drop_column('day_card', 'proof_logged')
    op.drop_column('day_card', 'followup_count')
    op.drop_column('day_card', 'outreach_count')

    # Remove fields from sprint
    op.drop_column('sprint', 'success_metrics')
    op.drop_column('sprint', 'mode')

    # Drop tables
    op.drop_index(op.f('ix_response_rule_pack_id'), table_name='response_rule')
    op.drop_table('response_rule')

    op.drop_index(op.f('ix_followup_task_status'), table_name='followup_task')
    op.drop_index(op.f('ix_followup_task_pack_id'), table_name='followup_task')
    op.drop_table('followup_task')

    op.drop_index(op.f('ix_subscription_user_id'), table_name='subscription')
    op.drop_table('subscription')
