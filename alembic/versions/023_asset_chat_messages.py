"""Add chat_messages to asset for poster/flyer conversation persistence.

Revision ID: 023
Revises: 022
Create Date: 2026-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asset", sa.Column("chat_messages", JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("asset", "chat_messages")
