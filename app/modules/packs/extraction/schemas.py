"""Pydantic schemas for brand extraction."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ContactInfo(BaseModel):
    """Contact information structure for brand profile."""
    
    model_config = ConfigDict(extra="forbid")
    
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class RawBrandProfile(BaseModel):
    """Raw brand profile extracted from website content by LLM."""
    
    model_config = ConfigDict(extra="forbid")

    brand_name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    products_or_services: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    value_proposition: Optional[str] = None
    brand_tone: Optional[str] = None
    mission_statement: Optional[str] = None
    geography: Optional[str] = None
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    social_links: List[str] = Field(default_factory=list)
    logo_url: Optional[str] = None


class WebsiteExtractedIngestionContactInfo(BaseModel):
    """Contact information extracted from website."""

    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class WebsiteExtractedIngestion(BaseModel):
    """Final merged brand profile after deterministic merge with metadata."""

    brand_name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    products_or_services: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    value_proposition: Optional[str] = None
    brand_tone: Optional[str] = None
    mission_statement: Optional[str] = None
    geography: Optional[str] = None
    contact_info: WebsiteExtractedIngestionContactInfo = Field(
        default_factory=WebsiteExtractedIngestionContactInfo
    )
    social_links: List[str] = Field(default_factory=list)
    logo_url: Optional[str] = None
    color_candidates: List[str] = Field(default_factory=list)


class ColorCandidate(BaseModel):
    """Color candidate with confidence score and metadata."""

    hex: str = Field(..., description="Hex color code (e.g. #ff0000)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    source: str = Field(..., description="Source of the color (e.g. 'asset', 'css', 'html')")
    rank: int = Field(..., ge=1, description="Ranking by relevance (1 is most relevant)")
