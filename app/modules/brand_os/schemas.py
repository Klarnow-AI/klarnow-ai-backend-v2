"""Brand OS Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.brand_os.domain_schema import (
    BrandFoundation,
    BrandStrategyProfile,
)
from app.modules.brand_os.models import BrandOS as BrandOSModel


class BrandOSRead(BaseModel):
    id: UUID
    pack_id: UUID
    version: str
    foundation: BrandFoundation
    brand_strategy: BrandStrategyProfile
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": False}


def brand_os_read_from_orm(row: BrandOSModel) -> BrandOSRead:
    """Build BrandOSRead from ORM row. Deserializes foundation/brand_strategy or builds from legacy."""
    foundation: BrandFoundation
    brand_strategy: BrandStrategyProfile
    if row.foundation and row.brand_strategy:
        try:
            foundation = BrandFoundation.model_validate(row.foundation)
            brand_strategy = BrandStrategyProfile.model_validate(row.brand_strategy)
        except Exception:
            foundation, brand_strategy = _legacy_to_foundation_and_strategy(row)
    else:
        foundation, brand_strategy = _legacy_to_foundation_and_strategy(row)
    return BrandOSRead(
        id=row.id,
        pack_id=row.pack_id,
        version=row.version,
        foundation=foundation,
        brand_strategy=brand_strategy,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _legacy_to_foundation_and_strategy(
    row: BrandOSModel,
) -> tuple[BrandFoundation, BrandStrategyProfile]:
    """Build minimal foundation and brand_strategy when JSON columns are missing or invalid."""
    from app.modules.brand_os.domain_schema import (
        MissionVision,
        AudiencePersona,
        PositioningDifferentiation,
        VoicePersonality,
        CoreMessagingHierarchy,
        StyleDirectionSeeds,
    )
    foundation = BrandFoundation(
        brand_name="",
        main_audience=[],
        one_line_offer="",
        brand_purpose=[],
        vision_12_month=[],
        brand_industry="",
    )
    brand_strategy = BrandStrategyProfile(
        mission_vision=MissionVision(
            mission="To be defined.",
            vision="To be defined.",
            promise="To be defined.",
        ),
        audience_personas=[],
        positioning_differentiation=PositioningDifferentiation(
            statement="",
            unique_advantage="",
        ),
        voice_personality=VoicePersonality(
            profile=[],
            archetype="",
            we_are=[],
            we_are_not=[],
        ),
        core_messaging_hierarchy=CoreMessagingHierarchy(
            elevator_pitch="",
            proof_points=[],
        ),
        style_direction_seeds=StyleDirectionSeeds(
            typography="",
            design_cues=[],
            palette=[],
        ),
    )
    return (foundation, brand_strategy)


class BrandOSList(BaseModel):
    items: list[BrandOSRead]
    total: int


class BrandOSUpdate(BaseModel):
    """Request body for PATCH: optional foundation and/or brand_strategy (merged into active)."""

    foundation: BrandFoundation | None = None
    brand_strategy: BrandStrategyProfile | None = None


class BrandOSSuggestRequest(BaseModel):
    """Request body for POST suggest: which field to suggest and optional current value."""

    field: str  # e.g. "mission_vision.mission", "positioning_differentiation.statement"
    current_value: str | None = None


class BrandOSSuggestResponse(BaseModel):
    suggestion: str
