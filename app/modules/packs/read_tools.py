"""Read-only tools for chat access to pack/account state."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import DomainNotFoundError
from app.modules.brand_os.services import get_active_for_pack as get_active_brand_os
from app.modules.builder.services import get_for_pack_any, get_published_for_pack
from app.modules.packs.models import Pack
from app.modules.packs.services import list_packs_for_user


GET_PACK_SNAPSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Project id"},
    },
    "required": ["pack_id"],
}

GET_ACCOUNT_SNAPSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "string", "format": "uuid", "description": "Current user id"},
        "pack_limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        "include_archived": {"type": "boolean", "default": False},
    },
    "required": ["user_id"],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_uuid(value: UUID | str) -> UUID:
    return UUID(str(value)) if isinstance(value, str) else value


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _normalize_limit(value: int | None, default: int, maximum: int) -> int:
    if value is None:
        return default
    return max(1, min(maximum, int(value)))


def _lead_payload(lead) -> dict:
    return {
        "id": str(lead.id),
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "status": lead.status,
        "pipeline_stage": lead.pipeline_stage,
        "summary": lead.summary,
        "due_date": lead.due_date.isoformat() if lead.due_date else None,
        "last_contacted_at": _iso(lead.last_contacted_at),
        "created_at": _iso(lead.created_at),
    }


def _pack_routes(pack_id: UUID) -> dict[str, str]:
    base = f"/projects/{pack_id}"
    return {
        "project": base,
        "docs": f"{base}/docs",
        "website": f"{base}/website",
        "brand_os": f"{base}/brand-os",
    }


def _status_counts(items: list, default_statuses: list[str]) -> dict[str, int]:
    counts = {k: 0 for k in default_statuses}
    for item in items:
        status = getattr(item, "status", None)
        if isinstance(status, str):
            counts[status] = counts.get(status, 0) + 1
    counts["total"] = len(items)
    return counts


def get_pack_snapshot(
    db: Session,
    pack_id: UUID | str,
    lead_limit: int = 20,
    task_limit: int = 20,
) -> dict:
    """Return a bounded snapshot of a single project's execution state."""
    pack_uuid = _safe_uuid(pack_id)
    pack = db.query(Pack).filter(Pack.id == pack_uuid).first()
    if not pack:
        raise DomainNotFoundError("Pack not found")

    _normalize_limit(lead_limit, default=20, maximum=50)
    _normalize_limit(task_limit, default=20, maximum=50)

    brand_os = get_active_brand_os(db, pack_uuid)

    published_site = get_published_for_pack(db, pack_uuid)
    draft_site = get_for_pack_any(db, pack_uuid)
    website_status = "none"
    if published_site:
        website_status = "published"
    elif draft_site:
        website_status = "draft"

    return {
        "scope": "project",
        "project": {
            "id": str(pack.id),
            "name": pack.name,
            "status": pack.status,
            "pack_type": pack.pack_type,
            "brand_name": pack.brand_name,
            "offer_one_liner": pack.offer_one_liner,
            "primary_cta": pack.primary_cta,
            "primary_pain": pack.primary_pain,
            "primary_outcome": pack.primary_outcome,
            "created_at": _iso(pack.created_at),
            "updated_at": _iso(pack.updated_at),
        },
        "workflow": {
            "onboarding_completed": pack.onboarding_completed_at is not None,
            "automation_ready": pack.onboarding_background_completed_at is not None,
        },
        "brand_os": {
            "active_version": brand_os.version if brand_os else None,
            "is_available": bool(brand_os),
        },
        "campaign": {
            "primary_cta": pack.primary_cta,
            "goal": pack.core_concept,
            "angles_count": 0,
            "is_available": bool((pack.primary_cta or "").strip()),
        },
        "website": {
            "status": website_status,
            "live_url": published_site.live_url if published_site else None,
            "published_at": _iso(published_site.published_at) if published_site else None,
        },
        "leads": {
            "counts": {"total": 0, "new": 0, "qualified": 0},
            "items": [],
        },
        "routes": _pack_routes(pack_uuid),
    }


def get_account_snapshot(
    db: Session,
    user_id: UUID | str,
    pack_limit: int = 20,
    task_limit: int = 30,
    include_archived: bool = False,
) -> dict:
    """Return account-wide summary across the user's projects."""
    user_uuid = _safe_uuid(user_id)
    pack_limit = _normalize_limit(pack_limit, default=20, maximum=50)

    packs = list_packs_for_user(db, user_uuid, include_archived=include_archived)
    selected_packs = packs[:pack_limit]

    pack_rows: list[dict] = []

    for pack in selected_packs:
        pack_rows.append(
            {
                "project_id": str(pack.id),
                "project_name": pack.name,
                "project_status": pack.status,
                "onboarding_completed": pack.onboarding_completed_at is not None,
                "automation_ready": pack.onboarding_background_completed_at is not None,
                "primary_cta": pack.primary_cta,
                "leads": {
                    "total": 0,
                    "new": 0,
                    "qualified": 0,
                },
                "routes": _pack_routes(pack.id),
            }
        )

    return {
        "scope": "account",
        "projects_total": len(packs),
        "projects_returned": len(selected_packs),
        "totals": {
            "leads": 0,
        },
        "projects": pack_rows,
        "routes": {"projects": "/projects"},
    }
