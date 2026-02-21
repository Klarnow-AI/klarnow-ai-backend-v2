"""Builder project API. CRUD for AI website builder projects (pack-scoped)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.clients.services import create_lead
from app.modules.public_site.schemas import PublicLeadCaptureBody, PublicLeadCaptureResponse
from app.modules.builder.schemas import (
    BuilderProjectCreate,
    BuilderProjectList,
    BuilderProjectRead,
    BuilderProjectUpdate,
)
from app.modules.builder.services import (
    get_for_pack,
    get_by_id,
    list_for_user,
    create,
    update,
    delete,
    publish,
    get_published,
    build_deploy_html,
)

# Public router — no auth, mounted at /p in main.py
public_router = APIRouter()

router = APIRouter()


def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


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
        return BuilderProjectRead.model_validate(existing)
    project = create(db, current_user.id, body.pack_id, body.name)
    return BuilderProjectRead.model_validate(project)


@router.get("/projects", response_model=BuilderProjectList)
def list_projects(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all builder projects for the authenticated user."""
    items = list_for_user(db, current_user.id)
    return BuilderProjectList(
        items=[BuilderProjectRead.model_validate(p) for p in items],
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
    return BuilderProjectRead.model_validate(project)


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
    return BuilderProjectRead.model_validate(project)


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
    return BuilderProjectRead.model_validate(project)


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
    """Publish a builder project, making it publicly accessible at /p/{project_id}."""
    project = get_by_id(db, project_id, current_user.id)
    if not project:
        raise NotFoundError("Builder project not found")
    live_url = str(request.base_url).rstrip("/") + f"/p/{project_id}"
    project = publish(db, project, live_url)
    return BuilderProjectRead.model_validate(project)


# ---------------------------------------------------------------------------
# Public site serving — no auth required
# ---------------------------------------------------------------------------

@public_router.get("/{project_id}", response_class=HTMLResponse)
def serve_published_site(project_id: UUID, db=Depends(get_db)):
    """Serve the published HTML for a builder project."""
    project = get_published(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Site not found or not yet published")
    return HTMLResponse(content=build_deploy_html(project.files, project_id=str(project.id)))


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
    project = get_published(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Site not found or not yet published")
    lead = create_lead(
        db,
        pack_id=project.pack_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        summary=body.summary,
        source="builder_site",
    )
    return PublicLeadCaptureResponse(lead_id=str(lead.id))
