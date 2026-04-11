"""Builder pack API. CRUD for AI website builder packs (pack-scoped)."""

from collections.abc import Mapping
from json import JSONDecodeError
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import BadRequestError, NotFoundError, ServiceUnavailableError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.builder.public_site_schemas import (
    PublicLeadCaptureBody,
    PublicLeadCaptureResponse,
    normalize_public_lead_payload,
)
from app.modules.builder.schemas import (
    BuilderGenerateRequest,
    BuilderPackCreate,
    BuilderPackList,
    BuilderPackRead,
    BuilderProjectUpdate,
)
from app.core.config import get_settings
from app.modules.builder.services import (
    build_deploy_html,
    build_site_shell_meta,
    create,
    delete,
    slug_from_name,
    ensure_unique_subdomain_slug,
    get_by_id,
    get_for_pack,
    get_published,
    list_for_user,
    load_published_html,
    load_published_metadata,
    load_published_snapshot,
    publish,
    publish_project_artifacts,
    remove_published_artifacts,
    unpublish,
    update,
)
from app.modules.builder.generation import create_website_generation_stream
from app.shared.services.generation_context import load_generation_brand_context

# Public router — no auth, mounted at /p in main.py
public_router = APIRouter()

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


def _project_response(
    pack,
    *,
    include_published_files: bool = False,
) -> BuilderPackRead:
    payload = BuilderPackRead.model_validate(pack).model_dump()
    payload["published_files"] = load_published_snapshot(pack) if include_published_files else None
    return BuilderPackRead(**payload)


async def _parse_public_lead_capture_request(request: Request) -> PublicLeadCaptureBody:
    content_type = (request.headers.get("content-type") or "").lower()
    payload: Mapping[str, object] | None = None

    if "application/json" in content_type or not content_type:
        try:
            json_body = await request.json()
        except (JSONDecodeError, ValueError, TypeError):
            json_body = None
        if isinstance(json_body, Mapping):
            payload = json_body

    if payload is None and (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
        or not content_type
    ):
        form = await request.form()
        payload = dict(form)

    return normalize_public_lead_payload(payload)


@router.post("/packs", response_model=BuilderPackRead, status_code=status.HTTP_201_CREATED)
def create_pack(
    body: BuilderPackCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a builder pack for a pack. One pack per pack."""
    _ensure_pack_access(db, body.pack_id, current_user.id)
    existing = get_for_pack(db, body.pack_id, current_user.id)
    if existing:
        return _project_response(existing, include_published_files=True)
    pack = create(db, current_user.id, body.pack_id, body.name)
    return _project_response(pack, include_published_files=True)


@router.get("/packs", response_model=BuilderPackList)
def list_projects(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all builder packs for the authenticated user."""
    items = list_for_user(db, current_user.id)
    return BuilderPackList(
        items=[_project_response(p, include_published_files=False) for p in items],
        total=len(items),
    )


@router.get("/packs/by-pack/{pack_id}", response_model=BuilderPackRead)
def get_project_by_pack(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the builder pack for a specific pack."""
    _ensure_pack_access(db, pack_id, current_user.id)
    pack = get_for_pack(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found for this pack")
    return _project_response(pack, include_published_files=True)


@router.get("/packs/{pack_id}", response_model=BuilderPackRead)
def get_project(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a builder pack by id."""
    pack = get_by_id(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found")
    return _project_response(pack, include_published_files=True)


@router.patch("/packs/{pack_id}", response_model=BuilderPackRead)
def update_pack(
    pack_id: UUID,
    body: BuilderProjectUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a builder pack (files, messages, name)."""
    pack = get_by_id(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found")
    data = body.model_dump(exclude_unset=True)
    try:
        pack = update(db, pack, **data)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    return _project_response(pack, include_published_files=True)


@router.delete("/packs/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pack(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a builder pack."""
    pack = get_by_id(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found")
    delete(db, pack)


@router.post("/packs/{pack_id}/publish", response_model=BuilderPackRead)
def publish_project(
    pack_id: UUID,
    request: Request,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a builder pack. When sites_domain is set, uses subdomain (brand name slug, fallback pack name); else /p/{pack_id}."""
    pack = get_by_id(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found")
    previous_subdomain_slug = pack.subdomain_slug
    pack = get_pack_for_user(db, pack.pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    settings = get_settings()
    if settings.sites_domain and settings.sites_domain.strip():
        display_name = (pack.brand_name or pack.name or "").strip() or "site"
        base_slug = slug_from_name(display_name)
        pack.subdomain_slug = ensure_unique_subdomain_slug(db, base_slug, pack.id)

    if pack.subdomain_slug and settings.sites_domain and settings.sites_domain.strip():
        live_url = f"https://{pack.subdomain_slug}.{settings.sites_domain.strip()}"
        lead_url = "/lead"
    else:
        live_url = str(request.base_url).rstrip("/") + f"/p/{pack_id}"
        lead_url = f"/p/{pack_id}/lead"

    brand_context = load_generation_brand_context(db, pack.pack_id, pack=pack)
    site_meta = build_site_shell_meta(
        brand_context,
        fallback_title=(pack.brand_name or pack.name or pack.name or "Website"),
    )
    pack = publish(
        db,
        pack,
        live_url,
        persist_published_files=False,
        commit=False,
    )
    try:
        used_storage = publish_project_artifacts(
            pack,
            lead_url=lead_url,
            previous_subdomain_slug=previous_subdomain_slug,
            site_meta=site_meta,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Failed to publish website assets") from exc
    if not used_storage:
        pack.published_files = dict(pack.files) if pack.files else {}
    db.commit()
    db.refresh(pack)
    return _project_response(pack, include_published_files=True)


@router.post("/packs/{pack_id}/unpublish", response_model=BuilderPackRead)
def unpublish_project(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpublish a builder pack. Clears live_url and subdomain; site will 404 until republished."""
    pack = get_by_id(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found")
    subdomain_slug = pack.subdomain_slug
    try:
        remove_published_artifacts(pack.id, subdomain_slug=subdomain_slug)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Failed to remove published website assets") from exc
    pack = unpublish(db, pack, commit=False)
    db.commit()
    db.refresh(pack)
    return _project_response(pack, include_published_files=True)


@router.post("/packs/{pack_id}/generate")
async def generate_project(
    pack_id: UUID,
    body: BuilderGenerateRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate builder pack code for the authenticated user's pack."""
    pack = get_by_id(db, pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Builder pack not found")

    pack = get_pack_for_user(db, pack.pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    if not body.messages:
        raise BadRequestError("Missing messages")
    if not body.files:
        raise BadRequestError("Missing files")

    brand_context = load_generation_brand_context(db, pack.pack_id, pack=pack)

    try:
        stream = await create_website_generation_stream(
            messages=body.messages,
            files=body.files,
            brand_context=brand_context,
            selected_style=body.selected_style,
            assistant_mode=body.assistant_mode,
        )
    except RuntimeError as exc:
        message = str(exc)
        if "not configured" in message.lower():
            raise ServiceUnavailableError(message) from exc
        raise ServiceUnavailableError(
            "We're having trouble generating right now. Please try again in a few moments."
        ) from exc

    return StreamingResponse(
        stream,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------
# Public site serving — no auth required
# ---------------------------------------------------------------------------

@public_router.get("/{pack_id}", response_class=HTMLResponse)
def serve_published_site(pack_id: UUID, db=Depends(get_db)):
    """Serve the published HTML for a builder pack."""
    html = load_published_html(pack_id=pack_id)
    if html is not None:
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
        )
    pack = get_published(db, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Site not found or not yet published")
    files = load_published_snapshot(pack) or dict(pack.published_files or pack.files or {})
    metadata = load_published_metadata(pack_id=pack_id) or {}
    brand_context = load_generation_brand_context(db, pack.pack_id)
    site_meta = build_site_shell_meta(
        brand_context,
        fallback_title=(brand_context.brand_name or pack.name or "Website"),
    )
    html = build_deploy_html(
        files,
        pack_id=str(pack.id),
        lead_url=str(metadata.get("lead_url") or f"/p/{pack_id}/lead"),
        site_title=str(metadata.get("site_title") or site_meta["site_title"]),
        favicon_href=str(metadata.get("favicon_href") or site_meta["favicon_href"] or ""),
        theme_color=str(metadata.get("theme_color") or site_meta["theme_color"] or ""),
    )
    try:
        publish_project_artifacts(
            pack,
            lead_url=str(metadata.get("lead_url") or f"/p/{pack_id}/lead"),
            site_meta={
                "site_title": str(metadata.get("site_title") or site_meta["site_title"]),
                "favicon_href": str(metadata.get("favicon_href") or site_meta["favicon_href"] or ""),
                "theme_color": str(metadata.get("theme_color") or site_meta["theme_color"] or ""),
            },
        )
    except Exception:
        pass
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
    )


@public_router.post(
    "/{pack_id}/lead",
    response_model=PublicLeadCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def capture_builder_lead(pack_id: UUID, request: Request, db=Depends(get_db)):
    """Capture a contact submission from a published builder site (no auth)."""
    body = await _parse_public_lead_capture_request(request)
    # Honeypot: bots often fill every field
    if body.website and str(body.website).strip():
        raise HTTPException(status_code=400, detail="Invalid form submission")
    if not (body.name and str(body.name).strip()):
        raise HTTPException(status_code=400, detail="Please provide your name")
    if not (body.email and str(body.email).strip()) and not (body.phone and str(body.phone).strip()):
        raise HTTPException(status_code=400, detail="Please provide at least an email or phone number")
    metadata = load_published_metadata(pack_id=pack_id)
    if not metadata and not get_published(db, pack_id):
        raise HTTPException(status_code=404, detail="Site not found or not yet published")
    submission_id = str(uuid4())
    return PublicLeadCaptureResponse(submission_id=submission_id, lead_id=submission_id)
