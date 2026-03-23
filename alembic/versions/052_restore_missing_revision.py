"""Restore missing revision 052.

Revision ID: 052
Revises: 051
Create Date: 2026-03-23

This is a no-op compatibility migration. Some databases are already stamped at
revision 052, but the checked-in migration history only reached 051. Keeping
this placeholder revision restores a valid Alembic graph without introducing
additional schema changes.
"""

from typing import Sequence, Union


revision: str = "052"
down_revision: Union[str, None] = "051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
