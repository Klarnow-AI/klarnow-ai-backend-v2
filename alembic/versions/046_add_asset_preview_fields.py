"""Add temporary preview fields for video assets.

Revision ID: 046
Revises: 045
Create Date: 2026-03-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "046"
down_revision: Union[str, None] = "045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "asset" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("asset")}
    if "preview_url" not in columns:
        op.add_column("asset", sa.Column("preview_url", sa.String(length=1024), nullable=True))
    if "preview_image_key" not in columns:
        op.add_column(
            "asset",
            sa.Column("preview_image_key", sa.String(length=512), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "asset" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("asset")}
    if "preview_image_key" in columns:
        op.drop_column("asset", "preview_image_key")
    if "preview_url" in columns:
        op.drop_column("asset", "preview_url")
