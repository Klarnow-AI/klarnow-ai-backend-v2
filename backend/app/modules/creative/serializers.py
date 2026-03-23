"""Creative asset response serialization helpers."""

from app.core.storage import get_asset_url
from app.modules.creative.schemas import AssetRead

ASSET_URL_TTL_SECONDS = 86400


def serialize_asset(asset) -> AssetRead:
    """Return API-safe asset payloads with durable playback URLs only."""
    payload = AssetRead.model_validate(asset).model_dump()
    payload["output_url"] = (
        get_asset_url(asset.output_key, expires_in=ASSET_URL_TTL_SECONDS)
        if asset.output_key
        else None
    )
    payload["poster_url"] = (
        get_asset_url(asset.preview_image_key, expires_in=ASSET_URL_TTL_SECONDS)
        if asset.preview_image_key
        else None
    )
    return AssetRead.model_validate(payload)
