"""One-shot database repair script.

Usage:
    python repair_db.py

Creates all missing tables and adds missing columns using raw SQL.
Safe to run multiple times (only creates/adds what's missing).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.model_registry import load_model_metadata
from sqlalchemy import create_engine, text, inspect

# Load all models into Base.metadata
load_model_metadata()

from app.modules.packs.models import User, Pack
from app.modules.brand_os.models import BrandOS
from app.modules.creative.models import Asset
from app.modules.builder.models import BuilderProject
from app.modules.agents.models import DecisionLog
from app.modules.waitlist.models import WaitlistSignup
from app.modules.docs.models import CompanyData, Document, DocumentSection
from app.modules.api_keys.models import ApiKey

settings = get_settings()
engine = create_engine(settings.database_url)


def _add_col(conn, table, column, definition):
    """Add a column if it doesn't exist."""
    conn.execute(text(f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='{table}' AND column_name='{column}'
            ) THEN
                ALTER TABLE "{table}" ADD COLUMN {column} {definition};
            END IF;
        END $$;
    """))


print(f"Connecting to: {settings.database_url[:40]}...")

with engine.connect() as conn:
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")

    # ----------------------------------------------------------------
    # 1. user - ensure all columns
    # ----------------------------------------------------------------
    if "user" in existing_tables:
        user_cols = {
            "google_sub": "VARCHAR(255)",
            "stripe_connect_account_id": "VARCHAR(255)",
            "stripe_connect_onboarding_complete": "BOOLEAN NOT NULL DEFAULT false",
            "stripe_customer_id": "VARCHAR(255)",
            "stripe_subscription_id": "VARCHAR(255)",
            "tier": "VARCHAR(32) NOT NULL DEFAULT 'free'",
            "tier_updated_at": "TIMESTAMP WITH TIME ZONE",
            "last_activity_at": "TIMESTAMP WITH TIME ZONE",
        }
        for col, typedef in user_cols.items():
            _add_col(conn, "user", col, typedef)
        conn.commit()
        print("  user: columns checked")

    # ----------------------------------------------------------------
    # 2. pack - ensure all columns
    # ----------------------------------------------------------------
    if "pack" in existing_tables:
        pack_cols = {
            "pack_type": "VARCHAR(32) DEFAULT 'enquiries'",
            "onboarding_answers": "JSON",
            "onboarding_completed_at": "TIMESTAMP WITH TIME ZONE",
            "onboarding_background_completed_at": "TIMESTAMP WITH TIME ZONE",
            "core_concept": "VARCHAR(500)",
            "active_brand_os_id": "UUID",
            "brand_name": "VARCHAR(255)",
            "offer_one_liner": "VARCHAR(500)",
            "target_audience": "VARCHAR(500)",
            "location_city": "VARCHAR(128)",
            "location_country": "VARCHAR(128)",
            "primary_cta": "VARCHAR(255)",
            "usp_category": "VARCHAR(64)",
            "usp_statement": "VARCHAR(500)",
            "usp_proof": "VARCHAR(500)",
            "usp_locked_line": "VARCHAR(600)",
            "proof_types": "JSON",
            "proof_text": "TEXT",
            "primary_pain": "VARCHAR(500)",
            "primary_outcome": "VARCHAR(500)",
            "hero_angle": "VARCHAR(64)",
            "business_type": "VARCHAR(32)",
            "website_url": "VARCHAR(512)",
            "has_existing_customers": "BOOLEAN",
            "day_0_completed_at": "TIMESTAMP WITH TIME ZONE",
        }
        for col, typedef in pack_cols.items():
            _add_col(conn, "pack", col, typedef)
        conn.commit()
        print("  pack: columns checked")

    # ----------------------------------------------------------------
    # 3. brand_os - ensure all columns
    # ----------------------------------------------------------------
    if "brand_os" in existing_tables:
        brand_os_cols = {
            "pack_id": "UUID",
            "version": "VARCHAR(16)",
            "source_job_id": "VARCHAR(64)",
            "foundation": "JSONB",
            "brand_strategy": "JSONB",
            "is_active": "BOOLEAN NOT NULL DEFAULT false",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in brand_os_cols.items():
            _add_col(conn, "brand_os", col, typedef)
        conn.commit()
        print("  brand_os: columns checked")

    # ----------------------------------------------------------------
    # 4. builder_project - ensure all columns
    # ----------------------------------------------------------------
    if "builder_project" in existing_tables:
        bp_cols = {
            "pack_id": "UUID",
            "user_id": "UUID",
            "name": "VARCHAR(255) DEFAULT 'Untitled Project'",
            "files": "JSON DEFAULT '{}'",
            "messages": "JSON DEFAULT '[]'",
            "published_files": "JSON",
            "live_url": "VARCHAR(2048)",
            "subdomain_slug": "VARCHAR(63)",
            "published_at": "TIMESTAMP WITH TIME ZONE",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
            "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in bp_cols.items():
            _add_col(conn, "builder_project", col, typedef)
        conn.commit()
        print("  builder_project: columns checked")

    # ----------------------------------------------------------------
    # 5. asset - ensure all columns
    # ----------------------------------------------------------------
    if "asset" in existing_tables:
        asset_cols = {
            "pack_id": "UUID",
            "type": "VARCHAR(32)",
            "version": "VARCHAR(16)",
            "name": "VARCHAR(256)",
            "template_id": "VARCHAR(128)",
            "source_code": "TEXT",
            "output_key": "VARCHAR(512)",
            "preview_url": "VARCHAR(1024)",
            "preview_image_key": "VARCHAR(512)",
            "script": "VARCHAR(8000)",
            "srt_key": "VARCHAR(512)",
            "sprint_day": "INTEGER",
            "chat_messages": "JSON",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in asset_cols.items():
            _add_col(conn, "asset", col, typedef)
        conn.commit()
        print("  asset: columns checked")

    # ----------------------------------------------------------------
    # 6. decision_log - ensure all columns
    # ----------------------------------------------------------------
    if "decision_log" in existing_tables:
        dl_cols = {
            "tool_name": "VARCHAR(128)",
            "agent": "VARCHAR(64)",
            "pack_id": "UUID",
            "inputs_sanitized": "JSON",
            "success": "BOOLEAN",
            "result_summary": "TEXT",
            "error_message": "TEXT",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in dl_cols.items():
            _add_col(conn, "decision_log", col, typedef)
        conn.commit()
        print("  decision_log: columns checked")

    # ----------------------------------------------------------------
    # 7. waitlist_signup - ensure all columns
    # ----------------------------------------------------------------
    if "waitlist_signup" in existing_tables:
        ws_cols = {
            "email": "VARCHAR(255)",
            "first_name": "VARCHAR(255)",
            "role": "VARCHAR(255)",
            "goal": "TEXT",
            "source": "VARCHAR(512)",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
            "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in ws_cols.items():
            _add_col(conn, "waitlist_signup", col, typedef)
        conn.commit()
        print("  waitlist_signup: columns checked")

    # ----------------------------------------------------------------
    # 8. company_data - ensure all columns
    # ----------------------------------------------------------------
    if "company_data" in existing_tables:
        cd_cols = {
            "pack_id": "UUID",
            "business_name": "VARCHAR(255)",
            "tagline": "VARCHAR(500)",
            "description": "TEXT",
            "address": "VARCHAR(500)",
            "phone": "VARCHAR(128)",
            "email": "VARCHAR(255)",
            "website": "VARCHAR(512)",
            "services": "JSON",
            "team_members": "JSON",
            "packages": "JSON",
            "standard_signatory": "JSON",
            "standard_footer": "TEXT",
            "logo_url": "VARCHAR(2048)",
            "logo_markup": "TEXT",
            "brand_voice": "VARCHAR(255)",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
            "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in cd_cols.items():
            _add_col(conn, "company_data", col, typedef)
        conn.commit()
        print("  company_data: columns checked")

    # ----------------------------------------------------------------
    # 9. document - ensure all columns
    # ----------------------------------------------------------------
    if "document" in existing_tables:
        doc_cols = {
            "pack_id": "UUID",
            "created_by_user_id": "UUID",
            "linked_document_id": "UUID",
            "type": "VARCHAR(64)",
            "status": "VARCHAR(32) DEFAULT 'draft'",
            "title": "VARCHAR(255)",
            "tone_preset": "VARCHAR(32) DEFAULT 'professional'",
            "start_mode": "VARCHAR(32) DEFAULT 'template'",
            "inputs_json": "JSON",
            "source_context_json": "JSON",
            "export_meta_json": "JSON",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
            "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in doc_cols.items():
            _add_col(conn, "document", col, typedef)
        conn.commit()
        print("  document: columns checked")

    # ----------------------------------------------------------------
    # 10. document_section - ensure all columns
    # ----------------------------------------------------------------
    if "document_section" in existing_tables:
        ds_cols = {
            "document_id": "UUID",
            "section_key": "VARCHAR(128)",
            "section_label": "VARCHAR(255)",
            "content": "TEXT DEFAULT ''",
            "order_index": "INTEGER DEFAULT 0",
            "metadata_json": "JSON",
            "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
            "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT now()",
        }
        for col, typedef in ds_cols.items():
            _add_col(conn, "document_section", col, typedef)
        conn.commit()
        print("  document_section: columns checked")

    # ----------------------------------------------------------------
    # 11. api_key - ensure all columns
    # ----------------------------------------------------------------
    if "api_key" in existing_tables:
        ak_cols = {
            "user_id": "UUID",
            "name": "VARCHAR(128)",
            "key_hash": "VARCHAR(64)",
            "key_prefix": "VARCHAR(12)",
            "is_active": "BOOLEAN NOT NULL DEFAULT true",
            "last_used_at": "TIMESTAMP WITH TIME ZONE",
            "usage_count": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()",
            "expires_at": "TIMESTAMP WITH TIME ZONE",
        }
        for col, typedef in ak_cols.items():
            _add_col(conn, "api_key", col, typedef)
        conn.commit()
        print("  api_key: columns checked")

# ----------------------------------------------------------------
# Create any entirely missing tables
# ----------------------------------------------------------------
print("\nRunning Base.metadata.create_all (creates missing tables only)...")
Base.metadata.create_all(engine, checkfirst=True)

# ----------------------------------------------------------------
# Add foreign keys that may be missing on existing tables
# ----------------------------------------------------------------
with engine.connect() as conn:
    fks = [
        ("fk_brand_os_pack_id", "brand_os", "pack_id", "pack(id)", "CASCADE"),
        ("fk_builder_project_pack_id", "builder_project", "pack_id", "pack(id)", "CASCADE"),
        ("fk_builder_project_user_id", "builder_project", "user_id", '"user"(id)', "CASCADE"),
        ("fk_asset_pack_id", "asset", "pack_id", "pack(id)", "CASCADE"),
        ("fk_decision_log_pack_id", "decision_log", "pack_id", "pack(id)", "SET NULL"),
        ("fk_company_data_pack_id", "company_data", "pack_id", "pack(id)", "CASCADE"),
        ("fk_document_pack_id", "document", "pack_id", "pack(id)", "CASCADE"),
        ("fk_document_user_id", "document", "created_by_user_id", '"user"(id)', "CASCADE"),
        ("fk_document_section_doc_id", "document_section", "document_id", "document(id)", "CASCADE"),
        ("fk_api_key_user_id", "api_key", "user_id", '"user"(id)', "CASCADE"),
    ]
    for name, table, col, ref, on_delete in fks:
        conn.execute(text(f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = '{name}' AND table_name = '{table}'
                ) THEN
                    BEGIN
                        ALTER TABLE "{table}" ADD CONSTRAINT {name}
                            FOREIGN KEY ({col}) REFERENCES {ref} ON DELETE {on_delete};
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END;
                END IF;
            END $$;
        """))
    conn.commit()
    print("Foreign key constraints checked.")

# ----------------------------------------------------------------
# Verify
# ----------------------------------------------------------------
inspector = inspect(engine)
final_tables = inspector.get_table_names()
print(f"\nFinal tables ({len(final_tables)}): {sorted(final_tables)}")

critical = [
    "user", "pack", "brand_os", "builder_project", "asset",
    "api_key", "waitlist_signup", "company_data", "document",
    "document_section", "decision_log",
]
for table in critical:
    if table in final_tables:
        cols = [c["name"] for c in inspector.get_columns(table)]
        print(f"  {table}: {len(cols)} columns OK")
    else:
        print(f"  {table}: MISSING!")

print("\nDone. Stamp alembic to 056 if needed:")
print("  alembic stamp 056")
