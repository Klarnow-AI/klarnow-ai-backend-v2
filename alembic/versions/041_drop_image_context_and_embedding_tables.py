"""Drop image-context and embedding retrieval tables.

Revision ID: 041
Revises: 040
Create Date: 2026-03-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "041"
down_revision: Union[str, Sequence[str], None] = "040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop known vector and status indexes first so table drops are clean across envs.
    op.execute("DROP INDEX IF EXISTS ix_global_image_context_item_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_global_image_context_item_status")
    op.execute("DROP INDEX IF EXISTS ix_image_context_item_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_image_context_item_pack_status")
    op.execute("DROP INDEX IF EXISTS ix_image_context_item_user_pack_status")
    op.execute("DROP INDEX IF EXISTS ix_image_context_job_pack_status")
    op.execute("DROP INDEX IF EXISTS ix_image_context_job_status_created")
    op.execute("DROP INDEX IF EXISTS asset_features_created_at_idx")
    op.execute("DROP INDEX IF EXISTS asset_features_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS asset_embeddings_512_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_global_asset_embeddings_512_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS global_asset_embeddings_512_embedding_ivfflat")

    op.execute("DROP TABLE IF EXISTS image_context_job CASCADE")
    op.execute("DROP TABLE IF EXISTS image_context_item CASCADE")
    op.execute("DROP TABLE IF EXISTS global_image_context_item CASCADE")
    op.execute("DROP TABLE IF EXISTS global_asset_embeddings_512 CASCADE")
    op.execute("DROP TABLE IF EXISTS global_assets CASCADE")
    op.execute("DROP TABLE IF EXISTS asset_embeddings_512 CASCADE")
    op.execute("DROP TABLE IF EXISTS asset_features CASCADE")


def downgrade() -> None:
    # Irreversible: dropped tables/data are intentionally removed.
    pass
