"""Launch Pack export schemas."""

from pydantic import BaseModel


class BuildLaunchPackBody(BaseModel):
    """Optional waiver if no proof in vault."""
    waiver_confirmed: bool = False


class BuildLaunchPackResponse(BaseModel):
    download_url: str
    expires_in_seconds: int
    pack_id: str
