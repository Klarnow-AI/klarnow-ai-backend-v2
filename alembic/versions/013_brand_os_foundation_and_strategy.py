"""Add brand_os foundation and brand_strategy columns with backfill.

Revision ID: 013
Revises: 012
Create Date: Brand OS schema alignment

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _build_foundation_from_legacy(mission: str | None, vision: str | None, values: dict | list | None) -> dict:
    """Build minimal BrandFoundation dict from legacy columns."""
    brand_purpose = []
    if isinstance(values, list):
        brand_purpose = [str(v) for v in values[:10]]
    elif isinstance(values, dict) and "values" in values:
        vv = values["values"]
        brand_purpose = [str(x) for x in (vv if isinstance(vv, list) else [vv])[:10]]
    return {
        "brand_name": "",
        "main_audience": [],
        "one_line_offer": "",
        "brand_purpose": brand_purpose,
        "vision_12_month": [v for v in (vision or "").split(". ") if v.strip()][:3] or [],
        "brand_industry": "",
    }


def _build_brand_strategy_from_legacy(
    mission: str | None,
    vision: str | None,
    values: dict | list | None,
    positioning: dict | None,
    personas: dict | list | None,
    voice_and_messaging: dict | None,
) -> dict:
    """Build minimal BrandStrategyProfile dict from legacy columns."""
    promise = ""
    if isinstance(values, dict) and values.get("promise"):
        promise = str(values["promise"])
    elif isinstance(values, list) and values:
        promise = str(values[0])
    mission_vision = {
        "mission": mission or "To be defined.",
        "vision": vision or "To be defined.",
        "promise": promise or "To be defined.",
    }
    audience_personas = []
    if isinstance(personas, list):
        for p in personas[:5]:
            if isinstance(p, dict):
                audience_personas.append({
                    "persona": p.get("name") or p.get("persona") or "Persona",
                    "needs": p.get("needs") or (p.get("description", "").split(",")[:5] if p.get("description") else []),
                    "pain_points": p.get("pain_points") or [],
                })
    pos = positioning or {}
    positioning_differentiation = {
        "statement": pos.get("statement") or pos.get("target_market") or "",
        "unique_advantage": pos.get("unique_advantage") or pos.get("differentiation") or "",
    }
    vam = voice_and_messaging or {}
    voice_personality = {
        "profile": vam.get("profile") or [],
        "archetype": vam.get("archetype") or "",
        "we_are": vam.get("we_are") or [],
        "we_are_not": vam.get("we_are_not") or [],
    }
    if isinstance(vam.get("tone"), str):
        voice_personality["profile"] = [vam["tone"]]
    core_messaging_hierarchy = {
        "elevator_pitch": vam.get("elevator_pitch") or "",
        "proof_points": vam.get("key_messages") or vam.get("proof_points") or [],
    }
    style_direction_seeds = {
        "typography": "",
        "design_cues": [],
        "palette": [],
    }
    return {
        "mission_vision": mission_vision,
        "audience_personas": audience_personas,
        "positioning_differentiation": positioning_differentiation,
        "voice_personality": voice_personality,
        "core_messaging_hierarchy": core_messaging_hierarchy,
        "style_direction_seeds": style_direction_seeds,
    }


def upgrade() -> None:
    op.add_column(
        "brand_os",
        sa.Column("foundation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "brand_os",
        sa.Column("brand_strategy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    conn = op.get_bind()
    rows = conn.execute(
        text(
            "SELECT id, mission, vision, values, positioning, personas, voice_and_messaging FROM brand_os"
        )
    ).fetchall()
    for row in rows:
        (row_id, mission, vision, values, positioning, personas, voice_and_messaging) = row
        foundation = _build_foundation_from_legacy(mission, vision, values)
        brand_strategy = _build_brand_strategy_from_legacy(
            mission, vision, values, positioning, personas, voice_and_messaging
        )
        conn.execute(
            text(
                "UPDATE brand_os SET foundation = CAST(:f AS jsonb), brand_strategy = CAST(:s AS jsonb) WHERE id = :id"
            ),
            {"f": json.dumps(foundation), "s": json.dumps(brand_strategy), "id": row_id},
        )
    # Keep nullable so existing app code can still create rows until deploy


def downgrade() -> None:
    op.drop_column("brand_os", "brand_strategy")
    op.drop_column("brand_os", "foundation")
