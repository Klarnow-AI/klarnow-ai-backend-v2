"""Routes for subdomain-based site serving. Mount at prefix '' so GET / and POST /lead work for builder subdomains."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.session import get_db
from app.modules.builder.public_site_schemas import PublicLeadCaptureResponse
from app.modules.builder.routes import _parse_public_lead_capture_request
from app.modules.builder.services import (
    build_deploy_html,
    build_site_shell_meta,
    get_published_by_subdomain,
    load_published_html,
    load_published_metadata,
    load_published_snapshot,
    publish_project_artifacts,
)
from app.shared.services.generation_context import load_generation_brand_context

router = APIRouter()


def _get_request_host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].strip().lower()


def _get_subdomain_from_host(host: str) -> str | None:
    """If host is {subdomain}.{sites_domain}, return subdomain; else None."""
    settings = get_settings()
    if not settings.sites_domain or not settings.sites_domain.strip():
        return None
    domain = settings.sites_domain.strip().lower()
    if not host or host == domain:
        return None
    suffix = "." + domain
    if not host.endswith(suffix):
        return None
    subdomain = host[: -len(suffix)]
    return subdomain if subdomain else None


def _resolve_host_site(
    request: Request,
    db: Session,
):
    host = _get_request_host(request)
    if not host:
        return None, None, None

    subdomain = _get_subdomain_from_host(host)
    if subdomain:
        project = get_published_by_subdomain(db, subdomain)
        if project:
            return project, "subdomain", subdomain

    return None, None, None


@router.get("/", response_class=HTMLResponse)
def serve_site_by_subdomain(
    request: Request,
    db: Session = Depends(get_db),
):
    """Serve the published builder site when Host matches a builder subdomain."""
    project, host_kind, host_value = _resolve_host_site(request, db)
    if not project or not host_kind or not host_value:
        raise HTTPException(status_code=404, detail="Not found")
    html = load_published_html(subdomain=host_value)
    if html is not None:
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=600"},
        )

    files = load_published_snapshot(project) or dict(project.published_files or project.files or {})
    metadata = load_published_metadata(subdomain=host_value) or {}
    brand_context = load_generation_brand_context(db, project.pack_id)
    site_meta = build_site_shell_meta(
        brand_context,
        fallback_title=(brand_context.brand_name or project.name or "Website"),
    )
    html = build_deploy_html(
        files,
        project_id=str(project.id),
        lead_url=str(metadata.get("lead_url") or "/lead"),
        site_title=str(metadata.get("site_title") or site_meta["site_title"]),
        favicon_href=str(metadata.get("favicon_href") or site_meta["favicon_href"] or ""),
        theme_color=str(metadata.get("theme_color") or site_meta["theme_color"] or ""),
    )
    try:
        publish_project_artifacts(
            project,
            lead_url=str(metadata.get("lead_url") or "/lead"),
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


@router.post("/lead", response_model=PublicLeadCaptureResponse, status_code=status.HTTP_201_CREATED)
async def capture_lead_by_subdomain(
    request: Request,
    db: Session = Depends(get_db),
):
    """Capture a contact submission from a subdomain-served builder site (no auth)."""
    body = await _parse_public_lead_capture_request(request)
    if body.website and str(body.website).strip():
        raise HTTPException(status_code=400, detail="Invalid form submission")
    if not (body.name and str(body.name).strip()):
        raise HTTPException(status_code=400, detail="Please provide your name")
    if not (body.email and str(body.email).strip()) and not (body.phone and str(body.phone).strip()):
        raise HTTPException(
            status_code=400,
            detail="Please provide at least an email or phone number",
        )
    project, host_kind, host_value = _resolve_host_site(request, db)
    if not project or not host_kind or not host_value:
        raise HTTPException(status_code=404, detail="Not found")
    submission_id = str(uuid4())
    return PublicLeadCaptureResponse(submission_id=submission_id, lead_id=submission_id)
