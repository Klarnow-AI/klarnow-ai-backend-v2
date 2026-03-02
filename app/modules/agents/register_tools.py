"""Register all domain tools with the registry. Call on app startup."""

from app.modules.agents.registry import ToolDef, register
from app.modules.brand_os.tools import generate_brand_os, GENERATE_BRAND_OS_SCHEMA
from app.modules.chat.tools import ask_day_question, ASK_DAY_QUESTION_SCHEMA
from app.modules.packs.tools import (
    update_pack,
    UPDATE_PACK_SCHEMA,
    extract_brand_from_url,
    EXTRACT_BRAND_SCHEMA,
)
from app.modules.sprint.tools import complete_sprint_day, COMPLETE_SPRINT_DAY_SCHEMA
from app.modules.creative.tools import (
    render_poster,
    render_video,
    RENDER_POSTER_SCHEMA,
    RENDER_VIDEO_SCHEMA,
)
from app.modules.revenue.tools import (
    create_proposal,
    create_invoice,
    CREATE_PROPOSAL_SCHEMA,
    CREATE_INVOICE_SCHEMA,
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
            description="Save pack fields from Day 0-3 (has_existing_brand, brand_url, brand_name, primary_cta, usp_statement, pitch_script, voice_notes_sent, etc). For brand_url with has_existing_brand=yes, triggers extraction. Call before complete_sprint_day.",
            parameters_schema=UPDATE_PACK_SCHEMA,
            fn=update_pack,
            allowed_agents=["orchestrator"],
            side_effects="Updates Pack fields, sets day_0_completed_at when Day 0 complete",
        )
    )
    register(
        ToolDef(
            name="complete_sprint_day",
            description="Mark sprint day 0-3 as complete and advance. Call after update_pack has saved the required fields.",
            parameters_schema=COMPLETE_SPRINT_DAY_SCHEMA,
            fn=complete_sprint_day,
            allowed_agents=["orchestrator"],
            side_effects="Marks DayCard complete, advances sprint.current_day",
        )
    )
    register(
        ToolDef(
            name="ask_day_question",
            description="When asking a Day 0-3 question, call this with field_key and day_context so the user gets input guidance and suggestion chips. Use re_suggest=true and previous_chips when user asks for different options.",
            parameters_schema=ASK_DAY_QUESTION_SCHEMA,
            fn=ask_day_question,
            allowed_agents=["orchestrator"],
            side_effects="None",
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
            name="create_proposal",
            description="Create a draft proposal for a pack (revenue).",
            parameters_schema=CREATE_PROPOSAL_SCHEMA,
            fn=create_proposal,
            allowed_agents=["orchestrator", "revenue"],
            side_effects="Creates Proposal row (draft)",
        )
    )
    register(
        ToolDef(
            name="create_invoice",
            description="Create a draft invoice for a pack (revenue).",
            parameters_schema=CREATE_INVOICE_SCHEMA,
            fn=create_invoice,
            allowed_agents=["orchestrator", "revenue"],
            side_effects="Creates Invoice row (draft)",
        )
    )
