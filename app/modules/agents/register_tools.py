"""Register all domain tools with the registry. Call on app startup."""

from app.modules.agents.registry import ToolDef, register
from app.modules.brand_os.tools import generate_brand_os, GENERATE_BRAND_OS_SCHEMA
from app.modules.conversion_page.tools import generate_conversion_page, GENERATE_CONVERSION_PAGE_SCHEMA
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
            name="generate_conversion_page",
            description="Generate a new conversion page version (React-driven structure). CTA must match campaign.primary_cta.",
            parameters_schema=GENERATE_CONVERSION_PAGE_SCHEMA,
            fn=generate_conversion_page,
            allowed_agents=["orchestrator", "conversion"],
            side_effects="Creates ConversionPage row",
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
