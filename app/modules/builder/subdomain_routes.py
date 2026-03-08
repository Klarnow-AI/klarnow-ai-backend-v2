"""Routes for subdomain-based site serving. Mount at prefix '' so GET / and POST /lead apply when Host is *.sites_domain."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.core.db.session import get_db
from sqlalchemy.orm import Session
from app.modules.builder.services import (
    build_deploy_html,
    get_published_by_subdomain,
    load_published_html,
    load_published_metadata,
    load_published_snapshot,
    publish_project_artifacts,
)
from app.modules.clients.services import create_lead
from app.modules.public_site.schemas import PublicLeadCaptureBody, PublicLeadCaptureResponse

router = APIRouter()


def _get_subdomain_from_host(request: Request) -> str | None:
    """If Host is {subdomain}.{sites_domain}, return subdomain; else None."""
    settings = get_settings()
    if not settings.sites_domain or not settings.sites_domain.strip():
        return None
    domain = settings.sites_domain.strip().lower()
    host = (request.headers.get("host") or "").split(":")[0].strip().lower()
    if not host or host == domain:
        return None
    suffix = "." + domain
    if not host.endswith(suffix):
        return None
    subdomain = host[: -len(suffix)]
    return subdomain if subdomain else None


@router.get("/", response_class=HTMLResponse)
def serve_site_by_subdomain(
    request: Request,
    db: Session = Depends(get_db),
):
    """Serve the published builder site when Host is {subdomain}.{sites_domain}."""
    subdomain = _get_subdomain_from_host(request)
    if subdomain is None:
        raise HTTPException(status_code=404, detail="Not found")
    html = load_published_html(subdomain=subdomain)
    if html is not None:
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
        )
    project = get_published_by_subdomain(db, subdomain)
    if not project:
        raise HTTPException(status_code=404, detail="Site not found or not yet published")
    files = load_published_snapshot(project) or dict(project.published_files or project.files or {})
    html = build_deploy_html(
        files,
        project_id=str(project.id),
        lead_url="/lead",
    )
    try:
        publish_project_artifacts(project, lead_url="/lead")
    except Exception:
        pass
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
    )


@router.post("/lead", response_model=PublicLeadCaptureResponse, status_code=status.HTTP_201_CREATED)
def capture_lead_by_subdomain(
    request: Request,
    body: PublicLeadCaptureBody,
    db: Session = Depends(get_db),
):
    """Capture a lead from a subdomain-served site (no auth)."""
    if body.website and str(body.website).strip():
        raise HTTPException(status_code=400, detail="Invalid form submission")
    if not (body.email and str(body.email).strip()) and not (body.phone and str(body.phone).strip()):
        raise HTTPException(
            status_code=400,
            detail="Please provide at least an email or phone number",
        )
    subdomain = _get_subdomain_from_host(request)
    if subdomain is None:
        raise HTTPException(status_code=404, detail="Not found")
    pack_id = None
    metadata = load_published_metadata(subdomain=subdomain)
    if metadata and metadata.get("pack_id"):
        try:
            pack_id = UUID(str(metadata["pack_id"]))
        except (TypeError, ValueError):
            pack_id = None
    if pack_id is None:
        project = get_published_by_subdomain(db, subdomain)
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
