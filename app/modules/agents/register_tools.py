"""Register all domain tools with the registry. Call on app startup."""

from app.modules.agents.registry import ToolDef, register
from app.modules.brand_os.tools import generate_brand_os, GENERATE_BRAND_OS_SCHEMA
from app.modules.packs.tools import (
    update_pack,
    UPDATE_PACK_SCHEMA,
    extract_brand_from_url,
    EXTRACT_BRAND_SCHEMA,
    get_onboarding_artifact_lineage,
    GET_ONBOARDING_ARTIFACT_LINEAGE_SCHEMA,
    rerun_onboarding_stage,
    RERUN_ONBOARDING_STAGE_SCHEMA,
    rerun_onboarding_from_qa,
    RERUN_ONBOARDING_FROM_QA_SCHEMA,
)
from app.modules.creative.tools import (
    render_poster,
    render_video,
    RENDER_POSTER_SCHEMA,
    RENDER_VIDEO_SCHEMA,
)
from app.modules.packs.read_tools import (
    get_pack_snapshot,
    get_account_snapshot,
    GET_PACK_SNAPSHOT_SCHEMA,
    GET_ACCOUNT_SNAPSHOT_SCHEMA,
)


def register_all_tools() -> None:
    register(
        ToolDef(
            name="extract_brand_from_url",
            description="Extract brand profile from website URL when user has existing brand (Day 0). Call when user provides a website URL after answering yes to 'Is this an existing brand?'. Merges extracted data into pack.",
            parameters_schema=EXTRACT_BRAND_SCHEMA,
            fn=extract_brand_from_url,
            allowed_agents=["orchestrator"],
            side_effects="Extracts brand from URL, merges into onboarding_answers and pack",
        )
    )
    register(
        ToolDef(
            name="update_pack",
            description="Save pack and onboarding fields such as has_existing_brand, brand_url, brand_name, primary_cta, proof_text, and related business context.",
            parameters_schema=UPDATE_PACK_SCHEMA,
            fn=update_pack,
            allowed_agents=["orchestrator"],
            side_effects="Updates Pack fields and onboarding context",
        )
    )
    register(
        ToolDef(
            name="generate_brand_os",
            description="Generate a new Brand OS version (A or B) for a pack from onboarding or existing context.",
            parameters_schema=GENERATE_BRAND_OS_SCHEMA,
            fn=generate_brand_os,
            allowed_agents=["orchestrator", "strategy"],
            side_effects="Creates BrandOS row, sets pack.active_brand_os_id",
        )
    )
    register(
        ToolDef(
            name="get_onboarding_artifact_lineage",
            description="Read the latest onboarding artifacts, their versions, and source stages for a project.",
            parameters_schema=GET_ONBOARDING_ARTIFACT_LINEAGE_SCHEMA,
            fn=get_onboarding_artifact_lineage,
            allowed_agents=["orchestrator", "strategy", "creative", "video"],
            side_effects="read-only",
        )
    )
    register(
        ToolDef(
            name="rerun_onboarding_stage",
            description="Queue a bounded onboarding repair from a named stage, optionally including downstream stages and QA.",
            parameters_schema=RERUN_ONBOARDING_STAGE_SCHEMA,
            fn=rerun_onboarding_stage,
            allowed_agents=["orchestrator", "strategy", "creative", "video"],
            side_effects="Queues a selective onboarding regeneration job",
        )
    )
    register(
        ToolDef(
            name="rerun_onboarding_from_qa",
            description="Use the latest QA report to queue the smallest repairable onboarding rerun.",
            parameters_schema=RERUN_ONBOARDING_FROM_QA_SCHEMA,
            fn=rerun_onboarding_from_qa,
            allowed_agents=["orchestrator", "strategy", "creative", "video"],
            side_effects="Queues a QA-driven selective onboarding regeneration job",
        )
    )
    register(
        ToolDef(
            name="render_poster",
            description="Render a poster/flyer asset. Compliance check on copy and CTA.",
            parameters_schema=RENDER_POSTER_SCHEMA,
            fn=render_poster,
            allowed_agents=["orchestrator", "creative"],
            side_effects="Creates Asset row, output to S3",
        )
    )
    register(
        ToolDef(
            name="render_video",
            description="Render 1-5 video assets. Compliance check. Safe area enforced.",
            parameters_schema=RENDER_VIDEO_SCHEMA,
            fn=render_video,
            allowed_agents=["orchestrator", "video"],
            side_effects="Creates Asset row(s), output MP4 + SRT to S3",
        )
    )
    register(
        ToolDef(
            name="get_pack_snapshot",
            description="Read-only snapshot of project execution state: strategy, CTA, website, proposals, invoices, and assets.",
            parameters_schema=GET_PACK_SNAPSHOT_SCHEMA,
            fn=get_pack_snapshot,
            allowed_agents=["orchestrator"],
            side_effects="read-only",
        )
    )
    register(
        ToolDef(
            name="get_account_snapshot",
            description="Read-only account-wide summary across the user's projects.",
            parameters_schema=GET_ACCOUNT_SNAPSHOT_SCHEMA,
            fn=get_account_snapshot,
            allowed_agents=["orchestrator"],
            side_effects="read-only",
        )
    )
