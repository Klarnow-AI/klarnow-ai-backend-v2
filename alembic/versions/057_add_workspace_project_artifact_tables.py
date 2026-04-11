"""Add workspace, project, and artifact domain tables.

Revision ID: 057
Revises: 056
Create Date: 2026-04-10

Introduces the new domain model for the productized multi-agent system:
  - workspace
  - project
  - generation_run
  - stage_run
  - artifact
  - approval
  - source_document
  - export_job

Uses IF NOT EXISTS to handle partial prior runs safely.
"""

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS workspace (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            owner_user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            settings JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_workspace_owner_user_id ON workspace (owner_user_id)
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS project (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            website_goal TEXT,
            recommended_website_type VARCHAR(50),
            selected_website_type VARCHAR(50),
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            onboarding_answers JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_project_workspace_id ON project (workspace_id)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_project_status ON project (status)
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS artifact (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            artifact_type VARCHAR(64) NOT NULL,
            version_number INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            schema_version INTEGER NOT NULL DEFAULT 1,
            json_payload JSONB NOT NULL,
            preview_file_id VARCHAR(512),
            created_by_stage VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_artifact_project_id ON artifact (project_id)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_artifact_artifact_type ON artifact (artifact_type)
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            ALTER TABLE artifact ADD CONSTRAINT uq_artifact_project_type_version
                UNIQUE (project_id, artifact_type, version_number);
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS generation_run (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            triggered_by_user_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'queued',
            pipeline_version VARCHAR(32),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_generation_run_project_id ON generation_run (project_id)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_generation_run_status ON generation_run (status)
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS stage_run (
            id UUID PRIMARY KEY,
            generation_run_id UUID NOT NULL REFERENCES generation_run(id) ON DELETE CASCADE,
            stage_name VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            depends_on_stage_names JSONB,
            model_id VARCHAR(128),
            prompt_version VARCHAR(64),
            temperature VARCHAR(8),
            input_artifact_ids JSONB,
            output_artifact_id UUID REFERENCES artifact(id) ON DELETE SET NULL,
            token_usage JSONB,
            latency_ms INTEGER,
            error_message TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_stage_run_generation_run_id ON stage_run (generation_run_id)
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS approval (
            id UUID PRIMARY KEY,
            artifact_id UUID NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            decision VARCHAR(32) NOT NULL,
            reason TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_approval_artifact_id ON approval (artifact_id)
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS source_document (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            name VARCHAR(512) NOT NULL,
            source_type VARCHAR(64),
            storage_path VARCHAR(1024) NOT NULL,
            mime_type VARCHAR(128),
            size_bytes INTEGER,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_source_document_project_id ON source_document (project_id)
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS export_job (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            export_type VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'queued',
            file_id VARCHAR(512),
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_export_job_project_id ON export_job (project_id)
    """))


def downgrade() -> None:
    op.drop_table("export_job")
    op.drop_table("source_document")
    op.drop_table("approval")
    op.drop_table("stage_run")
    op.drop_table("generation_run")
    op.drop_table("artifact")
    op.drop_table("project")
    op.drop_table("workspace")
