"""Full schema repair + add api_key table.

Revision ID: 056
Revises: 055
Create Date: 2026-04-05

Creates all missing tables with IF NOT EXISTS and adds missing columns
to handle databases in a partial migration state.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "056"
down_revision: str = "055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _exec(sql: str) -> None:
    op.get_bind().execute(sa.text(sql))


def _add_col_if_missing(table: str, column: str, definition: str) -> None:
    _exec(f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='{table}' AND column_name='{column}'
            ) THEN
                ALTER TABLE "{table}" ADD COLUMN {column} {definition};
            END IF;
        END $$;
    """)


def upgrade() -> None:
    # ----------------------------------------------------------------
    # 1. user (ensure all columns)
    # ----------------------------------------------------------------
    _add_col_if_missing("user", "google_sub", "VARCHAR(255) UNIQUE")
    _add_col_if_missing("user", "stripe_connect_account_id", "VARCHAR(255)")
    _add_col_if_missing("user", "stripe_connect_onboarding_complete", "BOOLEAN NOT NULL DEFAULT false")
    _add_col_if_missing("user", "stripe_customer_id", "VARCHAR(255)")
    _add_col_if_missing("user", "stripe_subscription_id", "VARCHAR(255)")
    _add_col_if_missing("user", "tier", "VARCHAR(32) NOT NULL DEFAULT 'free'")
    _add_col_if_missing("user", "tier_updated_at", "TIMESTAMP WITH TIME ZONE")
    _add_col_if_missing("user", "last_activity_at", "TIMESTAMP WITH TIME ZONE")

    # ----------------------------------------------------------------
    # 2. email_login_code
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS email_login_code (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            code VARCHAR(8) NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_email_login_code_email ON email_login_code (email);")

    # ----------------------------------------------------------------
    # 3. password_reset_token
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS password_reset_token (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            token VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_password_reset_token_email ON password_reset_token (email);")

    # ----------------------------------------------------------------
    # 4. refresh_token_session
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS refresh_token_session (
            id UUID NOT NULL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            last_used_at TIMESTAMP WITH TIME ZONE
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_refresh_token_session_user_id ON refresh_token_session (user_id);")

    # ----------------------------------------------------------------
    # 5. brand_os (MUST come before pack due to FK)
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS brand_os (
            id UUID NOT NULL PRIMARY KEY,
            pack_id UUID,
            version VARCHAR(16) NOT NULL,
            source_job_id VARCHAR(64),
            foundation JSONB,
            brand_strategy JSONB,
            is_active BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_brand_os_source_job_id ON brand_os (source_job_id);")

    # ----------------------------------------------------------------
    # 6. pack
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS pack (
            id UUID NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            status VARCHAR(64) NOT NULL DEFAULT 'draft',
            pack_type VARCHAR(32) NOT NULL DEFAULT 'enquiries',
            onboarding_answers JSON,
            onboarding_completed_at TIMESTAMP WITH TIME ZONE,
            onboarding_background_completed_at TIMESTAMP WITH TIME ZONE,
            core_concept VARCHAR(500),
            active_brand_os_id UUID REFERENCES brand_os(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            created_by_user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            brand_name VARCHAR(255),
            offer_one_liner VARCHAR(500),
            target_audience VARCHAR(500),
            location_city VARCHAR(128),
            location_country VARCHAR(128),
            primary_cta VARCHAR(255),
            usp_category VARCHAR(64),
            usp_statement VARCHAR(500),
            usp_proof VARCHAR(500),
            usp_locked_line VARCHAR(600),
            proof_types JSON,
            proof_text TEXT,
            primary_pain VARCHAR(500),
            primary_outcome VARCHAR(500),
            hero_angle VARCHAR(64),
            business_type VARCHAR(32),
            website_url VARCHAR(512),
            has_existing_customers BOOLEAN,
            day_0_completed_at TIMESTAMP WITH TIME ZONE
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_pack_created_by_user_id ON pack (created_by_user_id);")

    # Now add the FK from brand_os.pack_id -> pack.id if not present
    _exec("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_brand_os_pack_id' AND table_name = 'brand_os'
            ) THEN
                BEGIN
                    ALTER TABLE brand_os ADD CONSTRAINT fk_brand_os_pack_id
                        FOREIGN KEY (pack_id) REFERENCES pack(id) ON DELETE CASCADE;
                EXCEPTION WHEN duplicate_object THEN NULL;
                END;
            END IF;
        END $$;
    """)

    # ----------------------------------------------------------------
    # 7. asset
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS asset (
            id UUID NOT NULL PRIMARY KEY,
            pack_id UUID NOT NULL REFERENCES pack(id) ON DELETE CASCADE,
            type VARCHAR(32) NOT NULL,
            version VARCHAR(16),
            name VARCHAR(256),
            template_id VARCHAR(128),
            source_code TEXT,
            output_key VARCHAR(512),
            preview_url VARCHAR(1024),
            preview_image_key VARCHAR(512),
            script VARCHAR(8000),
            srt_key VARCHAR(512),
            sprint_day INTEGER,
            chat_messages JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    # ----------------------------------------------------------------
    # 8. builder_project
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS builder_project (
            id UUID NOT NULL PRIMARY KEY,
            pack_id UUID NOT NULL REFERENCES pack(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            name VARCHAR(255) DEFAULT 'Untitled Project',
            files JSON DEFAULT '{}',
            messages JSON DEFAULT '[]',
            published_files JSON,
            live_url VARCHAR(2048),
            subdomain_slug VARCHAR(63) UNIQUE,
            published_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)
    _exec("CREATE UNIQUE INDEX IF NOT EXISTS uq_builder_project_pack_id ON builder_project (pack_id);")
    _exec("CREATE INDEX IF NOT EXISTS ix_builder_project_subdomain_slug ON builder_project (subdomain_slug);")

    # ----------------------------------------------------------------
    # 9. decision_log
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS decision_log (
            id UUID NOT NULL PRIMARY KEY,
            tool_name VARCHAR(128) NOT NULL,
            agent VARCHAR(64) NOT NULL,
            pack_id UUID REFERENCES pack(id) ON DELETE SET NULL,
            inputs_sanitized JSON,
            success BOOLEAN NOT NULL,
            result_summary TEXT,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)

    # ----------------------------------------------------------------
    # 10. waitlist_signup
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS waitlist_signup (
            id UUID NOT NULL PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            first_name VARCHAR(255),
            role VARCHAR(255),
            goal TEXT,
            source VARCHAR(512),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_waitlist_signup_email ON waitlist_signup (email);")

    # ----------------------------------------------------------------
    # 11. company_data
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS company_data (
            id UUID NOT NULL PRIMARY KEY,
            pack_id UUID NOT NULL UNIQUE REFERENCES pack(id) ON DELETE CASCADE,
            business_name VARCHAR(255),
            tagline VARCHAR(500),
            description TEXT,
            address VARCHAR(500),
            phone VARCHAR(128),
            email VARCHAR(255),
            website VARCHAR(512),
            services JSON,
            team_members JSON,
            packages JSON,
            standard_signatory JSON,
            standard_footer TEXT,
            logo_url VARCHAR(2048),
            logo_markup TEXT,
            brand_voice VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_company_data_pack_id ON company_data (pack_id);")

    # ----------------------------------------------------------------
    # 12. document
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS document (
            id UUID NOT NULL PRIMARY KEY,
            pack_id UUID NOT NULL REFERENCES pack(id) ON DELETE CASCADE,
            created_by_user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            linked_document_id UUID REFERENCES document(id) ON DELETE SET NULL,
            type VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            title VARCHAR(255) NOT NULL,
            tone_preset VARCHAR(32) NOT NULL DEFAULT 'professional',
            start_mode VARCHAR(32) NOT NULL DEFAULT 'template',
            inputs_json JSON,
            source_context_json JSON,
            export_meta_json JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_document_pack_id ON document (pack_id);")
    _exec("CREATE INDEX IF NOT EXISTS ix_document_created_by_user_id ON document (created_by_user_id);")
    _exec("CREATE INDEX IF NOT EXISTS ix_document_type ON document (type);")
    _exec("CREATE INDEX IF NOT EXISTS ix_document_status ON document (status);")

    # ----------------------------------------------------------------
    # 13. document_section
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS document_section (
            id UUID NOT NULL PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
            section_key VARCHAR(128) NOT NULL,
            section_label VARCHAR(255) NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            order_index INTEGER NOT NULL DEFAULT 0,
            metadata_json JSON,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_document_section_document_id ON document_section (document_id);")

    # ----------------------------------------------------------------
    # 14. api_key (Phase 6)
    # ----------------------------------------------------------------
    _exec("""
        CREATE TABLE IF NOT EXISTS api_key (
            id UUID NOT NULL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            name VARCHAR(128) NOT NULL,
            key_hash VARCHAR(64) NOT NULL UNIQUE,
            key_prefix VARCHAR(12) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            last_used_at TIMESTAMP WITH TIME ZONE,
            usage_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            expires_at TIMESTAMP WITH TIME ZONE
        );
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_api_key_user_id ON api_key (user_id);")
    _exec("CREATE INDEX IF NOT EXISTS ix_api_key_key_hash ON api_key (key_hash);")


def downgrade() -> None:
    op.drop_table("api_key")
