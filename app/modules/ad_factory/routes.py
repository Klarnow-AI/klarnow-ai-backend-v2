"""Ad Factory V2 API routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.exc import DBAPIError, OperationalError

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import (
    NotFoundError,
    ServiceUnavailableError,
    map_value_error_to_app_error,
)
from app.modules.ad_factory.render_service import render_with_kling
from app.modules.ad_factory.services import generate_variants, get_render
from app.modules.packs.models import User

router = APIRouter()
_TRANSIENT_DB_ERROR_MARKERS = (
    "ssl error",
    "server closed the connection unexpectedly",
    "connection not open",
    "connection reset by peer",
    "could not receive data from server",
    "terminating connection due to administrator command",
)


def _is_transient_db_connection_error(exc: Exception) -> bool:
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_DB_ERROR_MARKERS)


class GenerateBody(BaseModel):
    pack_id: UUID


class RenderBody(BaseModel):
    variant_slots: list[str] = Field(..., min_length=1, max_length=3)


@router.post("/generate", response_model=dict)
def post_generate(
    body: GenerateBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate 3 ad variants. Runs Engines 0-5, validates, persists."""
    try:
        return generate_variants(db, body.pack_id, current_user.id)
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e
    except OperationalError as e:
        try:
            db.rollback()
        except Exception:
            pass
        if _is_transient_db_connection_error(e):
            raise ServiceUnavailableError(
                "Database connection dropped while saving ad variants. Please retry."
            ) from e
        raise


@router.post("/renders/{render_id}/render", response_model=dict)
def post_render(
    render_id: UUID,
    body: RenderBody,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Render selected variants via Kling and create Assets."""
    try:
        return render_with_kling(
            db,
            render_id,
            current_user.id,
            body.variant_slots,
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise map_value_error_to_app_error(e) from e


@router.get("/renders/{render_id}", response_model=dict)
def get_render_by_id(
    render_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full render contract by ID."""
    render = get_render(db, render_id, current_user.id)
    if not render:
        raise NotFoundError("Render not found")
    return {
        "render_id": str(render.id),
        "pack_id": str(render.pack_id),
        "status": render.status,
        "brand_brief": render.brand_brief_snapshot,
        "pack_snapshot": render.pack_snapshot,
        "variants": render.variants,
        "engines_output": render.engines_output,
        "render_metadata": render.render_metadata,
    }
