"""Builder project API. CRUD for AI website builder projects (pack-scoped)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import BadRequestError, NotFoundError, ServiceUnavailableError
from app.core.gates import can_generate_website
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.clients.services import create_lead
from app.modules.builder.public_site_schemas import (
    PublicLeadCaptureBody,
    PublicLeadCaptureResponse,
)
from app.modules.builder.schemas import (
    BuilderGenerateRequest,
    BuilderProjectCreate,
    BuilderProjectList,
    BuilderProjectRead,
    BuilderProjectUpdate,
)
from app.core.config import get_settings
from app.modules.builder.services import (
    build_deploy_html,
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
    project,
    *,
    include_published_files: bool = False,
) -> BuilderProjectRead:
    payload = BuilderProjectRead.model_validate(project).model_dump()
    payload["published_files"] = load_published_snapshot(project) if include_published_files else None
    return BuilderProjectRead(**payload)


@router.post("/projects", response_model=BuilderProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    body: BuilderProjectCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a builder project for a pack. One project per pack."""
    _ensure_pack_access(db, body.pack_id, current_user.id)
    existing = get_for_pack(db, body.pack_id, current_user.id)
    if existing:
        return _project_response(existing, include_published_files=True)
    project = create(db, current_user.id, body.pack_id, body.name)
    return _project_response(project, include_published_files=True)


@router.get("/projects", response_model=BuilderProjectList)
def list_projects(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all builder projects for the authenticated user."""
    items = list_for_user(db, current_user.id)
    return BuilderProjectList(
        items=[_project_response(p, include_published_files=False) for p in items],
        total=len(items),
    )


@router.get("/projects/by-pack/{pack_id}", response_model=BuilderProjectRead)
def get_project_by_pack(
    pack_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the builder project for a specific pack."""
    _ensure_pack_access(db, pack_id, current_user.id)
    project = get_for_pack(db, pack_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found for this pack")
    return _project_response(project, include_published_files=True)


@router.get("/projects/{project_id}", response_model=BuilderProjectRead)
def get_project(
    project_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a builder project by id."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")
    return _project_response(project, include_published_files=True)


@router.patch("/projects/{project_id}", response_model=BuilderProjectRead)
def update_project(
    project_id: UUID,
    body: BuilderProjectUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a builder project (files, messages, name)."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")
    data = body.model_dump(exclude_unset=True)
    project = update(db, project, **data)
    return _project_response(project, include_published_files=True)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a builder project."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")
    delete(db, project)


@router.post("/projects/{project_id}/publish", response_model=BuilderProjectRead)
def publish_project(
    project_id: UUID,
    request: Request,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a builder project. When sites_domain is set, uses subdomain (brand name slug, fallback pack name); else /p/{project_id}."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")
    previous_subdomain_slug = project.subdomain_slug
    settings = get_settings()
    if settings.sites_domain and settings.sites_domain.strip():
        pack = get_pack_for_user(db, project.pack_id, current_user.id)
        if not pack:
            raise NotFoundError("Pack not found")
        display_name = (pack.brand_name or pack.name or "").strip() or "site"
        base_slug = slug_from_name(display_name)
        project.subdomain_slug = ensure_unique_subdomain_slug(db, base_slug, project.id)
        live_url = f"https://{project.subdomain_slug}.{settings.sites_domain.strip()}"
    else:
        live_url = str(request.base_url).rstrip("/") + f"/p/{project_id}"
    lead_url = "/lead" if project.subdomain_slug else f"/p/{project_id}/lead"
    project = publish(
        db,
        project,
        live_url,
        persist_published_files=False,
        commit=False,
    )
    try:
        used_storage = publish_project_artifacts(
            project,
            lead_url=lead_url,
            previous_subdomain_slug=previous_subdomain_slug,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Failed to publish website assets") from exc
    if not used_storage:
        project.published_files = dict(project.files) if project.files else {}
    db.commit()
    db.refresh(project)
    return _project_response(project, include_published_files=True)


@router.post("/projects/{project_id}/unpublish", response_model=BuilderProjectRead)
def unpublish_project(
    project_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpublish a builder project. Clears live_url and subdomain; site will 404 until republished."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")
    subdomain_slug = project.subdomain_slug
    try:
        remove_published_artifacts(project.id, subdomain_slug=subdomain_slug)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Failed to remove published website assets") from exc
    project = unpublish(db, project, commit=False)
    db.commit()
    db.refresh(project)
    return _project_response(project, include_published_files=True)


@router.post("/projects/{project_id}/generate")
async def generate_project(
    project_id: UUID,
    body: BuilderGenerateRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate builder project code for the authenticated user's project."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")

    pack = get_pack_for_user(db, project.pack_id, current_user.id)
    if not pack:
        raise NotFoundError("Pack not found")
    if not body.messages:
        raise BadRequestError("Missing messages")
    if not body.files:
        raise BadRequestError("Missing files")

    can_generate_website(db, pack)
    brand_context = load_generation_brand_context(db, project.pack_id, pack=pack)

    try:
        stream = await create_website_generation_stream(
            messages=body.messages,
            files=body.files,
            brand_context=brand_context,
            selected_style=body.selected_style,
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

@public_router.get("/{project_id}", response_class=HTMLResponse)
def serve_published_site(project_id: UUID, db=Depends(get_db)):
    """Serve the published HTML for a builder project."""
    html = load_published_html(project_id=project_id)
    if html is not None:
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
        )
    project = get_published(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Site not found or not yet published")
    files = load_published_snapshot(project) or dict(project.published_files or project.files or {})
    html = build_deploy_html(files, project_id=str(project.id))
    try:
        publish_project_artifacts(project, lead_url=f"/p/{project_id}/lead")
    except Exception:
        pass
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
    )


@public_router.post(
    "/{project_id}/lead",
    response_model=PublicLeadCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
def capture_builder_lead(project_id: UUID, body: PublicLeadCaptureBody, db=Depends(get_db)):
    """Capture a lead submitted from a published builder site (no auth)."""
    # Honeypot: bots often fill every field
    if body.website and str(body.website).strip():
        raise HTTPException(status_code=400, detail="Invalid form submission")
    if not (body.email and str(body.email).strip()) and not (body.phone and str(body.phone).strip()):
        raise HTTPException(status_code=400, detail="Please provide at least an email or phone number")
    pack_id: UUID | None = None
    metadata = load_published_metadata(project_id=project_id)
    if metadata and metadata.get("pack_id"):
        try:
            pack_id = UUID(str(metadata["pack_id"]))
        except (TypeError, ValueError):
            pack_id = None
    if pack_id is None:
        project = get_published(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Site not found or not yet published")
        pack_id = project.pack_id
    lead = create_lead(
        db,
        pack_id=pack_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        summary=body.summary,
        source="builder_site",
    )
    return PublicLeadCaptureResponse(lead_id=str(lead.id))
