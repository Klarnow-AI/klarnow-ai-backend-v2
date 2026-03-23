


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "extensions";





SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."ad_factory_render" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "status" character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    "brand_brief_snapshot" "jsonb" NOT NULL,
    "pack_snapshot" "jsonb" NOT NULL,
    "selection_seed" character varying(128) NOT NULL,
    "pattern_ids_used" "jsonb",
    "hook_ids_used" "jsonb",
    "proof_strategy_id" character varying(64),
    "cta_id" character varying(64),
    "engines_output" "jsonb" NOT NULL,
    "variants" "jsonb" NOT NULL,
    "render_metadata" "jsonb",
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."ad_factory_render" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."alembic_version" (
    "version_num" character varying(32) NOT NULL
);


ALTER TABLE "public"."alembic_version" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."asset" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "type" character varying(32) NOT NULL,
    "version" character varying(16),
    "template_id" character varying(128),
    "output_key" character varying(512),
    "script" character varying(8000),
    "srt_key" character varying(512),
    "created_at" timestamp with time zone,
    "sprint_day" integer,
    "name" character varying(256),
    "source_code" "text",
    "chat_messages" json
);


ALTER TABLE "public"."asset" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."assets" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "org_id" "uuid" NOT NULL,
    "brand_id" "uuid",
    "source_url" "text" NOT NULL,
    "thumb_url" "text",
    "content_type" "text",
    "width" integer,
    "height" integer,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."assets" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."brand_os" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "version" character varying(16) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_at" timestamp with time zone,
    "foundation" "jsonb",
    "brand_strategy" "jsonb"
);


ALTER TABLE "public"."brand_os" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."builder_project" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "name" character varying(255) DEFAULT 'Untitled Project'::character varying,
    "files" json DEFAULT '{}'::json,
    "messages" json DEFAULT '[]'::json,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "live_url" "text",
    "published_at" timestamp with time zone,
    "subdomain_slug" character varying(63),
    "published_files" json
);


ALTER TABLE "public"."builder_project" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."campaign" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "version" character varying(16) NOT NULL,
    "primary_cta" character varying(255),
    "goal" "jsonb",
    "angles" json,
    "active_angle_id" character varying(64),
    "is_active" boolean NOT NULL,
    "created_at" timestamp with time zone
);


ALTER TABLE "public"."campaign" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_attachment" (
    "id" "uuid" NOT NULL,
    "conversation_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "file_name" character varying(255) NOT NULL,
    "content_type" character varying(255),
    "size_bytes" integer NOT NULL,
    "storage_key" character varying(1024),
    "text_content" "text",
    "created_at" timestamp with time zone
);


ALTER TABLE "public"."chat_attachment" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "name" character varying(255) NOT NULL,
    "email" character varying(255),
    "company" character varying(255),
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone
);


ALTER TABLE "public"."client" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversation" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "pack_id" "uuid",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "day_context" integer
);


ALTER TABLE "public"."conversation" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."day_card" (
    "id" "uuid" NOT NULL,
    "sprint_id" "uuid" NOT NULL,
    "day_number" integer NOT NULL,
    "ai_output" json,
    "user_action" "text",
    "definition_of_done" "text",
    "completed_at" timestamp with time zone,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone
);


ALTER TABLE "public"."day_card" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."decision_log" (
    "id" "uuid" NOT NULL,
    "tool_name" character varying(128) NOT NULL,
    "agent" character varying(64) NOT NULL,
    "pack_id" "uuid",
    "inputs_sanitized" json,
    "success" boolean NOT NULL,
    "result_summary" "text",
    "error_message" "text",
    "created_at" timestamp with time zone
);


ALTER TABLE "public"."decision_log" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."email_login_code" (
    "id" integer NOT NULL,
    "email" character varying(255) NOT NULL,
    "code" character varying(8) NOT NULL,
    "expires_at" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."email_login_code" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."email_login_code_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."email_login_code_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."email_login_code_id_seq" OWNED BY "public"."email_login_code"."id";



CREATE TABLE IF NOT EXISTS "public"."followup_task" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "lead_id" "uuid",
    "task_type" character varying(64) NOT NULL,
    "due_date" timestamp with time zone NOT NULL,
    "status" character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    "message_template" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    "template_key" character varying(64),
    "channel" character varying(32)
);


ALTER TABLE "public"."followup_task" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."invoice" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "client_id" "uuid",
    "status" character varying(32) NOT NULL,
    "amount" character varying(64) NOT NULL,
    "currency" character varying(8) NOT NULL,
    "due_date" "date",
    "content" "jsonb",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "stripe_invoice_id" character varying(255),
    "stripe_hosted_url" character varying(2048)
);


ALTER TABLE "public"."invoice" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."lead" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "client_id" "uuid",
    "name" character varying(255) NOT NULL,
    "phone" character varying(64),
    "email" character varying(255),
    "source" character varying(128),
    "status" character varying(32) DEFAULT 'new'::character varying NOT NULL,
    "summary" "text",
    "budget_range" character varying(128),
    "urgency" character varying(64),
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "pipeline_stage" character varying(32) DEFAULT 'contacted'::character varying NOT NULL,
    "due_date" "date",
    "deal_value" numeric(14,2),
    "assigned_user_id" "uuid",
    "last_contacted_at" timestamp with time zone
);


ALTER TABLE "public"."lead" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."message" (
    "id" "uuid" NOT NULL,
    "conversation_id" "uuid" NOT NULL,
    "role" character varying(32) NOT NULL,
    "content" "text",
    "tool_calls" json,
    "tool_results" json,
    "is_preview" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone,
    "attachments" json
);


ALTER TABLE "public"."message" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."pack" (
    "id" "uuid" NOT NULL,
    "name" character varying(255) NOT NULL,
    "status" character varying(64) NOT NULL,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "created_by_user_id" "uuid" NOT NULL,
    "onboarding_answers" json,
    "onboarding_completed_at" timestamp with time zone,
    "active_brand_os_id" "uuid",
    "active_campaign_id" "uuid",
    "client_id" "uuid",
    "pack_type" character varying(32) DEFAULT 'enquiries'::character varying NOT NULL,
    "core_concept" character varying(500),
    "brand_name" character varying(255),
    "offer_one_liner" character varying(500),
    "target_audience" character varying(500),
    "location_city" character varying(128),
    "location_country" character varying(128),
    "primary_cta" character varying(255),
    "usp_category" character varying(64),
    "usp_statement" character varying(500),
    "usp_proof" character varying(500),
    "usp_locked_line" character varying(600),
    "proof_types" json,
    "proof_text" "text",
    "primary_pain" character varying(500),
    "primary_outcome" character varying(500),
    "hero_angle" character varying(64),
    "business_type" character varying(32),
    "day_0_completed_at" timestamp with time zone,
    "website_url" character varying(512),
    "has_existing_customers" boolean,
    "onboarding_background_completed_at" timestamp with time zone
);


ALTER TABLE "public"."pack" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."password_reset_token" (
    "id" integer NOT NULL,
    "email" character varying(255) NOT NULL,
    "token" character varying(255) NOT NULL,
    "expires_at" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."password_reset_token" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."password_reset_token_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."password_reset_token_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."password_reset_token_id_seq" OWNED BY "public"."password_reset_token"."id";



CREATE TABLE IF NOT EXISTS "public"."proof" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "file_key" character varying(512) NOT NULL,
    "tags" character varying[],
    "uploaded_at" timestamp with time zone,
    "proof_text" "text"
);


ALTER TABLE "public"."proof" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."proposal" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "client_id" "uuid",
    "status" character varying(32) NOT NULL,
    "amount" character varying(64) NOT NULL,
    "currency" character varying(8) NOT NULL,
    "due_date" "date",
    "content" "jsonb",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone
);


ALTER TABLE "public"."proposal" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."response_rule" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "trigger" character varying(64) NOT NULL,
    "response_template" "text" NOT NULL,
    "locked_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."response_rule" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."sprint" (
    "id" "uuid" NOT NULL,
    "pack_id" "uuid" NOT NULL,
    "status" character varying(32) NOT NULL,
    "current_day" integer NOT NULL,
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "mode" character varying(32) DEFAULT 'build'::character varying NOT NULL,
    "success_metrics" json
);


ALTER TABLE "public"."sprint" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."subscription" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "plan" character varying(32) DEFAULT 'free'::character varying NOT NULL,
    "credits_remaining" integer DEFAULT 0 NOT NULL,
    "credits_total" integer DEFAULT 0 NOT NULL,
    "cycle_start_date" timestamp with time zone,
    "cycle_end_date" timestamp with time zone,
    "status" character varying(32) DEFAULT 'active'::character varying NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."subscription" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."support_request" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid",
    "email" character varying(255) NOT NULL,
    "topic" character varying(128) NOT NULL,
    "manual_topic" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."support_request" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user" (
    "id" "uuid" NOT NULL,
    "email" character varying(255) NOT NULL,
    "hashed_password" character varying(255) NOT NULL,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "stripe_connect_account_id" character varying(255),
    "stripe_connect_onboarding_complete" boolean DEFAULT false NOT NULL,
    "last_activity_at" timestamp with time zone,
    "google_sub" character varying(255)
);


ALTER TABLE "public"."user" OWNER TO "postgres";


ALTER TABLE ONLY "public"."email_login_code" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."email_login_code_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."password_reset_token" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."password_reset_token_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."ad_factory_render"
    ADD CONSTRAINT "ad_factory_render_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."alembic_version"
    ADD CONSTRAINT "alembic_version_pkc" PRIMARY KEY ("version_num");



ALTER TABLE ONLY "public"."asset"
    ADD CONSTRAINT "asset_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."assets"
    ADD CONSTRAINT "assets_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."brand_os"
    ADD CONSTRAINT "brand_os_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."builder_project"
    ADD CONSTRAINT "builder_project_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."campaign"
    ADD CONSTRAINT "campaign_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chat_attachment"
    ADD CONSTRAINT "chat_attachment_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client"
    ADD CONSTRAINT "client_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conversation"
    ADD CONSTRAINT "conversation_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."day_card"
    ADD CONSTRAINT "day_card_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."decision_log"
    ADD CONSTRAINT "decision_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."email_login_code"
    ADD CONSTRAINT "email_login_code_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."followup_task"
    ADD CONSTRAINT "followup_task_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."invoice"
    ADD CONSTRAINT "invoice_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."lead"
    ADD CONSTRAINT "lead_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."message"
    ADD CONSTRAINT "message_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."pack"
    ADD CONSTRAINT "pack_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."password_reset_token"
    ADD CONSTRAINT "password_reset_token_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."proof"
    ADD CONSTRAINT "proof_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."proposal"
    ADD CONSTRAINT "proposal_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."response_rule"
    ADD CONSTRAINT "response_rule_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."sprint"
    ADD CONSTRAINT "sprint_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subscription"
    ADD CONSTRAINT "subscription_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subscription"
    ADD CONSTRAINT "subscription_user_id_key" UNIQUE ("user_id");



ALTER TABLE ONLY "public"."support_request"
    ADD CONSTRAINT "support_request_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."builder_project"
    ADD CONSTRAINT "uq_builder_project_pack_id" UNIQUE ("pack_id");



ALTER TABLE ONLY "public"."day_card"
    ADD CONSTRAINT "uq_day_card_sprint_day" UNIQUE ("sprint_id", "day_number");



ALTER TABLE ONLY "public"."user"
    ADD CONSTRAINT "user_pkey" PRIMARY KEY ("id");



CREATE INDEX "assets_brand_id_idx" ON "public"."assets" USING "btree" ("brand_id");



CREATE INDEX "assets_org_id_idx" ON "public"."assets" USING "btree" ("org_id");



CREATE INDEX "ix_ad_factory_render_pack_id" ON "public"."ad_factory_render" USING "btree" ("pack_id");



CREATE INDEX "ix_asset_pack_id" ON "public"."asset" USING "btree" ("pack_id");



CREATE INDEX "ix_brand_os_pack_id" ON "public"."brand_os" USING "btree" ("pack_id");



CREATE UNIQUE INDEX "ix_builder_project_subdomain_slug" ON "public"."builder_project" USING "btree" ("subdomain_slug");



CREATE INDEX "ix_campaign_pack_id" ON "public"."campaign" USING "btree" ("pack_id");



CREATE INDEX "ix_chat_attachment_conversation_id" ON "public"."chat_attachment" USING "btree" ("conversation_id");



CREATE INDEX "ix_chat_attachment_user_id" ON "public"."chat_attachment" USING "btree" ("user_id");



CREATE INDEX "ix_client_user_id" ON "public"."client" USING "btree" ("user_id");



CREATE INDEX "ix_conversation_pack_id" ON "public"."conversation" USING "btree" ("pack_id");



CREATE INDEX "ix_conversation_user_id" ON "public"."conversation" USING "btree" ("user_id");



CREATE INDEX "ix_day_card_sprint_id" ON "public"."day_card" USING "btree" ("sprint_id");



CREATE INDEX "ix_decision_log_pack_id" ON "public"."decision_log" USING "btree" ("pack_id");



CREATE INDEX "ix_decision_log_tool_name" ON "public"."decision_log" USING "btree" ("tool_name");



CREATE INDEX "ix_email_login_code_email" ON "public"."email_login_code" USING "btree" ("email");



CREATE INDEX "ix_followup_task_pack_id" ON "public"."followup_task" USING "btree" ("pack_id");



CREATE INDEX "ix_followup_task_status" ON "public"."followup_task" USING "btree" ("status");



CREATE INDEX "ix_invoice_pack_id" ON "public"."invoice" USING "btree" ("pack_id");



CREATE INDEX "ix_invoice_stripe_invoice_id" ON "public"."invoice" USING "btree" ("stripe_invoice_id");



CREATE INDEX "ix_lead_pack_id" ON "public"."lead" USING "btree" ("pack_id");



CREATE INDEX "ix_lead_pipeline_stage" ON "public"."lead" USING "btree" ("pipeline_stage");



CREATE INDEX "ix_lead_status" ON "public"."lead" USING "btree" ("status");



CREATE INDEX "ix_message_conversation_id" ON "public"."message" USING "btree" ("conversation_id");



CREATE INDEX "ix_pack_created_by_user_id" ON "public"."pack" USING "btree" ("created_by_user_id");



CREATE INDEX "ix_password_reset_token_email" ON "public"."password_reset_token" USING "btree" ("email");



CREATE UNIQUE INDEX "ix_password_reset_token_token" ON "public"."password_reset_token" USING "btree" ("token");



CREATE INDEX "ix_proof_pack_id" ON "public"."proof" USING "btree" ("pack_id");



CREATE INDEX "ix_proposal_pack_id" ON "public"."proposal" USING "btree" ("pack_id");



CREATE INDEX "ix_response_rule_pack_id" ON "public"."response_rule" USING "btree" ("pack_id");



CREATE INDEX "ix_sprint_pack_id" ON "public"."sprint" USING "btree" ("pack_id");



CREATE UNIQUE INDEX "ix_subscription_user_id" ON "public"."subscription" USING "btree" ("user_id");



CREATE INDEX "ix_support_request_email" ON "public"."support_request" USING "btree" ("email");



CREATE INDEX "ix_support_request_user_id" ON "public"."support_request" USING "btree" ("user_id");



CREATE UNIQUE INDEX "ix_user_email" ON "public"."user" USING "btree" ("email");



CREATE UNIQUE INDEX "ix_user_google_sub" ON "public"."user" USING "btree" ("google_sub");



CREATE INDEX "ix_user_stripe_connect_account_id" ON "public"."user" USING "btree" ("stripe_connect_account_id");



ALTER TABLE ONLY "public"."ad_factory_render"
    ADD CONSTRAINT "ad_factory_render_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."asset"
    ADD CONSTRAINT "asset_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."brand_os"
    ADD CONSTRAINT "brand_os_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."builder_project"
    ADD CONSTRAINT "builder_project_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."builder_project"
    ADD CONSTRAINT "builder_project_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."campaign"
    ADD CONSTRAINT "campaign_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chat_attachment"
    ADD CONSTRAINT "chat_attachment_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversation"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chat_attachment"
    ADD CONSTRAINT "chat_attachment_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client"
    ADD CONSTRAINT "client_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversation"
    ADD CONSTRAINT "conversation_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."conversation"
    ADD CONSTRAINT "conversation_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."day_card"
    ADD CONSTRAINT "day_card_sprint_id_fkey" FOREIGN KEY ("sprint_id") REFERENCES "public"."sprint"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."decision_log"
    ADD CONSTRAINT "decision_log_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."lead"
    ADD CONSTRAINT "fk_lead_assigned_user_id_user" FOREIGN KEY ("assigned_user_id") REFERENCES "public"."user"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."pack"
    ADD CONSTRAINT "fk_pack_active_brand_os" FOREIGN KEY ("active_brand_os_id") REFERENCES "public"."brand_os"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."pack"
    ADD CONSTRAINT "fk_pack_active_campaign" FOREIGN KEY ("active_campaign_id") REFERENCES "public"."campaign"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."pack"
    ADD CONSTRAINT "fk_pack_client_id_client" FOREIGN KEY ("client_id") REFERENCES "public"."client"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."followup_task"
    ADD CONSTRAINT "followup_task_lead_id_fkey" FOREIGN KEY ("lead_id") REFERENCES "public"."lead"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."followup_task"
    ADD CONSTRAINT "followup_task_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."invoice"
    ADD CONSTRAINT "invoice_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."client"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."invoice"
    ADD CONSTRAINT "invoice_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."lead"
    ADD CONSTRAINT "lead_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."client"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."lead"
    ADD CONSTRAINT "lead_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."message"
    ADD CONSTRAINT "message_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversation"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."pack"
    ADD CONSTRAINT "pack_created_by_user_id_fkey" FOREIGN KEY ("created_by_user_id") REFERENCES "public"."user"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."proof"
    ADD CONSTRAINT "proof_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."proposal"
    ADD CONSTRAINT "proposal_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."client"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."proposal"
    ADD CONSTRAINT "proposal_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."response_rule"
    ADD CONSTRAINT "response_rule_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."sprint"
    ADD CONSTRAINT "sprint_pack_id_fkey" FOREIGN KEY ("pack_id") REFERENCES "public"."pack"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."subscription"
    ADD CONSTRAINT "subscription_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."support_request"
    ADD CONSTRAINT "support_request_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE SET NULL;





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";










































































































































































































































































































































































































































































































































GRANT ALL ON TABLE "public"."ad_factory_render" TO "anon";
GRANT ALL ON TABLE "public"."ad_factory_render" TO "authenticated";
GRANT ALL ON TABLE "public"."ad_factory_render" TO "service_role";



GRANT ALL ON TABLE "public"."alembic_version" TO "anon";
GRANT ALL ON TABLE "public"."alembic_version" TO "authenticated";
GRANT ALL ON TABLE "public"."alembic_version" TO "service_role";



GRANT ALL ON TABLE "public"."asset" TO "anon";
GRANT ALL ON TABLE "public"."asset" TO "authenticated";
GRANT ALL ON TABLE "public"."asset" TO "service_role";



GRANT ALL ON TABLE "public"."assets" TO "anon";
GRANT ALL ON TABLE "public"."assets" TO "authenticated";
GRANT ALL ON TABLE "public"."assets" TO "service_role";



GRANT ALL ON TABLE "public"."brand_os" TO "anon";
GRANT ALL ON TABLE "public"."brand_os" TO "authenticated";
GRANT ALL ON TABLE "public"."brand_os" TO "service_role";



GRANT ALL ON TABLE "public"."builder_project" TO "anon";
GRANT ALL ON TABLE "public"."builder_project" TO "authenticated";
GRANT ALL ON TABLE "public"."builder_project" TO "service_role";



GRANT ALL ON TABLE "public"."campaign" TO "anon";
GRANT ALL ON TABLE "public"."campaign" TO "authenticated";
GRANT ALL ON TABLE "public"."campaign" TO "service_role";



GRANT ALL ON TABLE "public"."chat_attachment" TO "anon";
GRANT ALL ON TABLE "public"."chat_attachment" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_attachment" TO "service_role";



GRANT ALL ON TABLE "public"."client" TO "anon";
GRANT ALL ON TABLE "public"."client" TO "authenticated";
GRANT ALL ON TABLE "public"."client" TO "service_role";



GRANT ALL ON TABLE "public"."conversation" TO "anon";
GRANT ALL ON TABLE "public"."conversation" TO "authenticated";
GRANT ALL ON TABLE "public"."conversation" TO "service_role";



GRANT ALL ON TABLE "public"."day_card" TO "anon";
GRANT ALL ON TABLE "public"."day_card" TO "authenticated";
GRANT ALL ON TABLE "public"."day_card" TO "service_role";



GRANT ALL ON TABLE "public"."decision_log" TO "anon";
GRANT ALL ON TABLE "public"."decision_log" TO "authenticated";
GRANT ALL ON TABLE "public"."decision_log" TO "service_role";



GRANT ALL ON TABLE "public"."email_login_code" TO "anon";
GRANT ALL ON TABLE "public"."email_login_code" TO "authenticated";
GRANT ALL ON TABLE "public"."email_login_code" TO "service_role";



GRANT ALL ON SEQUENCE "public"."email_login_code_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."email_login_code_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."email_login_code_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."followup_task" TO "anon";
GRANT ALL ON TABLE "public"."followup_task" TO "authenticated";
GRANT ALL ON TABLE "public"."followup_task" TO "service_role";



GRANT ALL ON TABLE "public"."invoice" TO "anon";
GRANT ALL ON TABLE "public"."invoice" TO "authenticated";
GRANT ALL ON TABLE "public"."invoice" TO "service_role";



GRANT ALL ON TABLE "public"."lead" TO "anon";
GRANT ALL ON TABLE "public"."lead" TO "authenticated";
GRANT ALL ON TABLE "public"."lead" TO "service_role";



GRANT ALL ON TABLE "public"."message" TO "anon";
GRANT ALL ON TABLE "public"."message" TO "authenticated";
GRANT ALL ON TABLE "public"."message" TO "service_role";



GRANT ALL ON TABLE "public"."pack" TO "anon";
GRANT ALL ON TABLE "public"."pack" TO "authenticated";
GRANT ALL ON TABLE "public"."pack" TO "service_role";



GRANT ALL ON TABLE "public"."password_reset_token" TO "anon";
GRANT ALL ON TABLE "public"."password_reset_token" TO "authenticated";
GRANT ALL ON TABLE "public"."password_reset_token" TO "service_role";



GRANT ALL ON SEQUENCE "public"."password_reset_token_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."password_reset_token_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."password_reset_token_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."proof" TO "anon";
GRANT ALL ON TABLE "public"."proof" TO "authenticated";
GRANT ALL ON TABLE "public"."proof" TO "service_role";



GRANT ALL ON TABLE "public"."proposal" TO "anon";
GRANT ALL ON TABLE "public"."proposal" TO "authenticated";
GRANT ALL ON TABLE "public"."proposal" TO "service_role";



GRANT ALL ON TABLE "public"."response_rule" TO "anon";
GRANT ALL ON TABLE "public"."response_rule" TO "authenticated";
GRANT ALL ON TABLE "public"."response_rule" TO "service_role";



GRANT ALL ON TABLE "public"."sprint" TO "anon";
GRANT ALL ON TABLE "public"."sprint" TO "authenticated";
GRANT ALL ON TABLE "public"."sprint" TO "service_role";



GRANT ALL ON TABLE "public"."subscription" TO "anon";
GRANT ALL ON TABLE "public"."subscription" TO "authenticated";
GRANT ALL ON TABLE "public"."subscription" TO "service_role";



GRANT ALL ON TABLE "public"."support_request" TO "anon";
GRANT ALL ON TABLE "public"."support_request" TO "authenticated";
GRANT ALL ON TABLE "public"."support_request" TO "service_role";



GRANT ALL ON TABLE "public"."user" TO "anon";
GRANT ALL ON TABLE "public"."user" TO "authenticated";
GRANT ALL ON TABLE "public"."user" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































drop extension if exists "pg_net";
