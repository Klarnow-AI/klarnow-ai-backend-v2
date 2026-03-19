"""AI-generated proposal draft content from pack + optional lead context."""

import json
from datetime import date, timedelta
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.modules.brand_os.services import get_active_for_pack, get_context_strings
from app.modules.clients.models import Client, Lead
from app.modules.clients.services import get_lead_by_pack_and_client
from app.modules.packs.models import Pack
from app.shared.services.reference_kb import get_reference_kb
from app.shared.services.openai_compatible import (
    create_sync_openai_client,
    get_default_model,
    has_openai_compatible_provider,
)

logger = get_logger("klarnow.revenue.proposal_generation")


class ProposalLineItem(TypedDict, total=False):
    label: str
    amount: str | None
    description: str


class ProposalGeneratedContent(TypedDict, total=False):
    description: str
    line_items: list[ProposalLineItem]
    terms: str
    notes: str


class ProposalGenerateResult(TypedDict):
    content: ProposalGeneratedContent
    suggested_amount: str | None
    suggested_due_date: str | None
    references: list[dict[str, Any]]


def _build_pack_context(pack: Pack, brand_os: Any) -> dict[str, Any]:
    """Build pack context dict for proposal generation."""
    ctx: dict[str, Any] = {
        "pack_name": pack.name,
        "brand_name": pack.brand_name or "Our Brand",
        "offer_one_liner": pack.offer_one_liner or "",
        "target_audience": pack.target_audience or "",
        "primary_cta": pack.primary_cta or "",
        "business_type": pack.business_type or "service",
    }
    if pack.usp_locked_line:
        ctx["usp_locked_line"] = pack.usp_locked_line
    if pack.usp_statement:
        ctx["usp_statement"] = pack.usp_statement
    if pack.usp_proof:
        ctx["usp_proof"] = pack.usp_proof
    if pack.primary_pain:
        ctx["primary_pain"] = pack.primary_pain
    if pack.primary_outcome:
        ctx["primary_outcome"] = pack.primary_outcome
    if pack.hero_angle:
        ctx["hero_angle"] = pack.hero_angle
    if pack.location_city:
        ctx["location_city"] = pack.location_city
    if pack.location_country:
        ctx["location_country"] = pack.location_country
    if brand_os:
        mission, _, _, voice_str = get_context_strings(brand_os)
        if mission:
            ctx["mission"] = mission
        if voice_str:
            ctx["voice_str"] = voice_str
    return ctx


def _build_lead_context(lead: Lead | None, client: Client | None) -> dict[str, Any]:
    """Build lead/client context for proposal generation."""
    if not lead and not client:
        return {}
    ctx: dict[str, Any] = {}
    if lead:
        ctx["lead_name"] = lead.name
        if lead.summary:
            ctx["lead_summary"] = lead.summary
        if lead.budget_range:
            ctx["budget_range"] = lead.budget_range
        if lead.deal_value is not None:
            ctx["deal_value"] = str(lead.deal_value)
        if lead.urgency:
            ctx["urgency"] = lead.urgency
        if lead.due_date:
            ctx["lead_due_date"] = lead.due_date.isoformat()
    if client:
        ctx["client_name"] = client.name
        if client.company:
            ctx["client_company"] = client.company
    return ctx


def _build_reference_query(pack_ctx: dict[str, Any], lead_ctx: dict[str, Any]) -> str:
    """Compose retrieval query for global reference KB."""
    parts: list[str] = [
        str(pack_ctx.get("brand_name") or ""),
        str(pack_ctx.get("offer_one_liner") or ""),
        str(pack_ctx.get("target_audience") or ""),
        str(pack_ctx.get("primary_cta") or ""),
        str(pack_ctx.get("usp_statement") or ""),
        str(pack_ctx.get("primary_pain") or ""),
        str(pack_ctx.get("primary_outcome") or ""),
        str(lead_ctx.get("lead_summary") or ""),
        str(lead_ctx.get("budget_range") or ""),
        str(lead_ctx.get("urgency") or ""),
    ]
    return "\n".join([p for p in parts if p.strip()])


def _get_reference_context(
    pack_ctx: dict[str, Any],
    lead_ctx: dict[str, Any],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Retrieve optional markdown KB snippets for proposal grounding."""
    query = _build_reference_query(pack_ctx, lead_ctx)
    if not query.strip():
        return None, []
    try:
        payload = get_reference_kb().retrieve(query)
    except Exception as e:
        logger.warning("proposal_reference_retrieval_failed: %s", e)
        return None, []
    context_text = payload.get("context_text") if isinstance(payload, dict) else None
    references = payload.get("references") if isinstance(payload, dict) else None
    if not isinstance(context_text, str):
        context_text = None
    if not isinstance(references, list):
        references = []
    return context_text, references


def _build_prompt(
    pack_ctx: dict[str, Any],
    lead_ctx: dict[str, Any],
    *,
    reference_context: str | None = None,
) -> str:
    """Build user prompt for proposal content generation."""
    lines = [
        "Generate a short, professional proposal draft for the following context.",
        "",
        "PACK / BRAND:",
        f"- Pack name: {pack_ctx.get('pack_name', 'N/A')}",
        f"- Brand: {pack_ctx.get('brand_name', 'N/A')}",
        f"- Offer: {pack_ctx.get('offer_one_liner', 'N/A')}",
        f"- Target audience: {pack_ctx.get('target_audience', 'N/A')}",
        f"- Business type: {pack_ctx.get('business_type', 'service')}",
    ]
    if pack_ctx.get("usp_statement"):
        lines.append(f"- USP: {pack_ctx['usp_statement']}")
    if pack_ctx.get("primary_pain"):
        lines.append(f"- Primary pain: {pack_ctx['primary_pain']}")
    if pack_ctx.get("primary_outcome"):
        lines.append(f"- Primary outcome: {pack_ctx['primary_outcome']}")

    if lead_ctx:
        lines.append("")
        lines.append("LEAD / CLIENT:")
        if lead_ctx.get("client_name"):
            lines.append(f"- Client: {lead_ctx['client_name']}" + (f" ({lead_ctx['client_company']})" if lead_ctx.get("client_company") else ""))
        if lead_ctx.get("lead_summary"):
            lines.append(f"- Summary: {lead_ctx['lead_summary']}")
        if lead_ctx.get("budget_range"):
            lines.append(f"- Budget range: {lead_ctx['budget_range']}")
        if lead_ctx.get("deal_value"):
            lines.append(f"- Deal value: {lead_ctx['deal_value']}")
        if lead_ctx.get("urgency"):
            lines.append(f"- Urgency: {lead_ctx['urgency']}")

    if reference_context:
        lines.extend([
            "",
            "GLOBAL REFERENCE DOCUMENT EXCERPTS:",
            reference_context,
            "",
            "Use the reference excerpts when relevant for factual grounding.",
            "If excerpts are not relevant to this proposal, continue with best professional judgment.",
        ])

    lines.extend([
        "",
        "Return ONLY a JSON object with this exact structure (no markdown, no explanation):",
        '{',
        '  "content": {',
        '    "description": "2-4 sentence proposal summary addressing the client and the offer",',
        '    "line_items": [',
        '      {"label": "Item name", "amount": "500.00", "description": "Brief description"},',
        '      {"label": "Another item", "amount": null, "description": "Optional line without amount"}',
        '    ],',
        '    "terms": "Optional payment/terms note (1-2 sentences, or empty string)",',
        '    "notes": "Optional internal or client-facing notes (or empty string)"',
        '  },',
        '  "suggested_amount": "1500.00",  // total amount as string, or null if not inferrable',
        '  "suggested_due_date": "YYYY-MM-DD"  // date string or null',
        '}',
    ])
    return "\n".join(lines)


def _stub_result(
    references: list[dict[str, Any]] | None = None,
) -> ProposalGenerateResult:
    """Return a stub when API key is missing or generation fails."""
    return ProposalGenerateResult(
        content=ProposalGeneratedContent(
            description="Proposal content could not be generated. Configure OPENROUTER_API_KEY or add content manually.",
            line_items=[],
            terms="",
            notes="",
        ),
        suggested_amount=None,
        suggested_due_date=None,
        references=references or [],
    )


def generate_proposal_draft(
    db: Session,
    pack: Pack,
    user_id: Any,
    client_id: Any = None,
) -> ProposalGenerateResult:
    """
    Generate proposal draft content and suggested amount/due_date from pack and optional lead.

    Args:
        db: DB session
        pack: Pack (must have access checked by caller)
        user_id: Current user UUID (for client lookup)
        client_id: Optional client UUID; if set, lead for pack+client is used for context

    Returns:
        ProposalGenerateResult with content (description, line_items, terms, notes),
        suggested_amount, and suggested_due_date. Stub returned if AI is not configured.
    """
    if not has_openai_compatible_provider():
        logger.warning("OPENROUTER_API_KEY not configured; returning stub proposal draft")
        return _stub_result()

    brand_os = get_active_for_pack(db, pack.id)
    pack_ctx = _build_pack_context(pack, brand_os)

    lead: Lead | None = None
    client: Client | None = None
    if client_id:
        from app.modules.clients.services import get_for_user
        client = get_for_user(db, client_id, user_id)
        lead = get_lead_by_pack_and_client(db, pack.id, client_id)
        if not client and lead and lead.client_id:
            client = db.query(Client).filter(Client.id == lead.client_id).first()
    lead_ctx = _build_lead_context(lead, client)
    reference_context, references = _get_reference_context(pack_ctx, lead_ctx)

    # Default suggested_due_date: +14 days if we have nothing from lead
    default_due = (date.today() + timedelta(days=14)).isoformat()
    if lead_ctx.get("lead_due_date"):
        default_due = lead_ctx["lead_due_date"]

    try:
        client_openai = create_sync_openai_client()
        if not client_openai:
            return _stub_result(references=references)
        prompt = _build_prompt(
            pack_ctx,
            lead_ctx,
            reference_context=reference_context,
        )
        response = client_openai.chat.completions.create(
            model=get_default_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional proposal writer. Generate concise, client-ready proposal content. "
                        "Return only valid JSON with the exact keys: content (with description, line_items, terms, notes), "
                        "suggested_amount (string or null), suggested_due_date (YYYY-MM-DD or null). "
                        "Suggested amount should reflect lead's deal_value or budget_range when available; otherwise a reasonable total. "
                        "No markdown, no code fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content
        if not raw:
            return _stub_result(references=references)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1] if "\n" in raw else raw[3:]
        if raw.startswith("json"):
            raw = raw[4:]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        content = data.get("content") or {}
        if not isinstance(content, dict):
            content = {"description": str(content), "line_items": [], "terms": "", "notes": ""}
        result = ProposalGenerateResult(
            content=ProposalGeneratedContent(
                description=content.get("description") or "",
                line_items=content.get("line_items") or [],
                terms=content.get("terms") or "",
                notes=content.get("notes") or "",
            ),
            suggested_amount=data.get("suggested_amount") if isinstance(data.get("suggested_amount"), str) else None,
            suggested_due_date=data.get("suggested_due_date") if isinstance(data.get("suggested_due_date"), str) else None,
            references=references,
        )
        if not result["suggested_due_date"] and (lead_ctx or True):
            result["suggested_due_date"] = default_due
        return result
    except json.JSONDecodeError as e:
        logger.warning("Proposal generation JSON parse error: %s", e)
        return _stub_result(references=references)
    except Exception as e:
        logger.exception("Proposal generation failed: %s", e)
        return _stub_result(references=references)
