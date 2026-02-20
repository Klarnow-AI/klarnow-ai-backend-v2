"""Brand OS domain schema: canonical Pydantic models for generation and API."""

from pydantic import BaseModel, Field


class BrandFoundation(BaseModel):
    brand_name: str = Field(default="", description="The brand's full official name.")
    main_audience: list[str] = Field(
        default_factory=list,
        description="Primary target audiences or customer segments (e.g. 'small business owners', 'e-commerce founders').",
    )
    one_line_offer: str = Field(
        default="",
        description="Single sentence describing what the brand does and for whom (e.g. 'We help X do Y so they can Z').",
    )
    brand_purpose: list[str] = Field(
        default_factory=list,
        description="Core values and principles that drive the brand (3-5 short phrases).",
    )
    vision_12_month: list[str] = Field(
        default_factory=list,
        description="Concrete goals and milestones the brand aims to achieve within 12 months.",
    )
    brand_industry: str = Field(
        default="",
        description="Industry or market category (e.g. 'SaaS', 'professional services', 'e-commerce').",
    )


class MissionVision(BaseModel):
    mission: str = Field(..., description="Mission statement.")
    vision: str = Field(..., description="Vision statement (may include target metrics).")
    promise: str = Field(..., description="Brand promise / commitment.")


class AudiencePersona(BaseModel):
    persona: str = Field(..., description="Persona name/title.")
    needs: list[str] = Field(default_factory=list, description="Persona needs.")
    pain_points: list[str] = Field(default_factory=list, description="Persona pain points.")


class PositioningDifferentiation(BaseModel):
    statement: str = Field(..., description="Positioning statement.")
    unique_advantage: str = Field(..., description="Unique advantage / differentiation.")


class VoicePersonality(BaseModel):
    profile: list[str] = Field(default_factory=list, description="Voice profile tags.")
    archetype: str = Field(..., description="Brand archetype.")
    we_are: list[str] = Field(default_factory=list, description="Traits the brand embodies.")
    we_are_not: list[str] = Field(default_factory=list, description="Traits the brand avoids.")


class CoreMessagingHierarchy(BaseModel):
    elevator_pitch: str = Field(..., description="Short core pitch.")
    proof_points: list[str] = Field(
        default_factory=list, description="Key proof points / claims."
    )


class StyleDirectionSeeds(BaseModel):
    typography: str = Field(..., description="Primary typeface and style.")
    design_cues: list[str] = Field(default_factory=list, description="Design cues/tags.")
    palette: list[str] = Field(default_factory=list, description="Color palette tags/names.")


class BrandStrategyProfile(BaseModel):
    mission_vision: MissionVision
    audience_personas: list[AudiencePersona] = Field(default_factory=list)
    positioning_differentiation: PositioningDifferentiation
    voice_personality: VoicePersonality
    core_messaging_hierarchy: CoreMessagingHierarchy
    style_direction_seeds: StyleDirectionSeeds


class BrandOS(BaseModel):
    """Logical Brand OS: foundation + brand strategy. Used for LLM structured output."""

    foundation: BrandFoundation
    brand_strategy: BrandStrategyProfile
