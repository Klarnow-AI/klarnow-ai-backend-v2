"""Ad Factory V2 API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.ad_factory.render_service import render_with_kling
from app.modules.ad_factory.services import generate_variants, get_render
from app.modules.packs.models import User

router = APIRouter()


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
    """Generate 3 ad variants. Runs Engines 0-5, validates, persists. No credits consumed."""
    try:
        return generate_variants(db, body.pack_id, current_user.id)
    except ValueError as e:
        raise NotFoundError(str(e))


@router.post("/renders/{render_id}/render", response_model=dict)
def post_render(
    render_id: UUID,
    body: RenderBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Render selected variants via Kling. Deducts credits, creates Assets."""
    try:
        return render_with_kling(db, render_id, current_user.id, body.variant_slots)
    except ValueError as e:
        raise NotFoundError(str(e))


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
