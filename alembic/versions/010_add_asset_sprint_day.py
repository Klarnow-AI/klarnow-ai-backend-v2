"""Add sprint_day to asset table (1-7 for 7-day sprint)."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, Sequence[str], None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "asset",
        sa.Column("sprint_day", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("asset", "sprint_day")
