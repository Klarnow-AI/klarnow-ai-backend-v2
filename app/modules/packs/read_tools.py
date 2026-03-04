"""Read-only tools for chat access to pack/account state."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.brand_os.services import get_active_for_pack as get_active_brand_os
from app.modules.builder.services import get_for_pack_any, get_published_for_pack
from app.modules.campaign.services import get_active_for_pack as get_active_campaign
from app.modules.clients.models import LEAD_STATUS_NEW, LEAD_STATUS_QUALIFIED
from app.modules.clients.services import list_leads_for_pack
from app.modules.packs.models import Pack
from app.modules.packs.services import list_packs_for_user
from app.modules.revenue.services import list_invoices_for_pack, list_proposals_for_pack
from app.modules.sprint.services import get_active_sprint_for_pack
from app.modules.tasks.services import get_overdue_tasks, get_pending_tasks_sorted_for_queue


GET_PACK_SNAPSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "lead_limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        "task_limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        "revenue_limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
    },
    "required": ["pack_id"],
}

GET_PACK_FOLLOWUP_QUEUE_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "status": {
            "type": "string",
            "description": "Queue filter: pending or overdue",
            "enum": ["pending", "overdue"],
            "default": "pending",
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30},
    },
    "required": ["pack_id"],
}

GET_ACCOUNT_SNAPSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": {"type": "string", "format": "uuid", "description": "Current user id"},
        "pack_limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        "task_limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30},
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


def _task_payload(task, lead_name: str | None = None) -> dict:
    now = _now()
    due = task.due_date
    if due < now:
        urgency = "overdue"
    elif due.date() == now.date():
        urgency = "due_today"
    else:
        urgency = "upcoming"
    return {
        "id": str(task.id),
        "pack_id": str(task.pack_id),
        "lead_id": str(task.lead_id) if task.lead_id else None,
        "lead_name": lead_name,
        "task_type": task.task_type,
        "status": task.status,
        "due_date": _iso(task.due_date),
        "urgency": urgency,
        "channel": task.channel,
        "template_key": task.template_key,
        "message_template": task.message_template,
    }


def _proposal_payload(proposal) -> dict:
    return {
        "id": str(proposal.id),
        "status": proposal.status,
        "amount": proposal.amount,
        "currency": proposal.currency,
        "due_date": proposal.due_date.isoformat() if proposal.due_date else None,
        "created_at": _iso(proposal.created_at),
    }


def _invoice_payload(invoice) -> dict:
    return {
        "id": str(invoice.id),
        "status": invoice.status,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "created_at": _iso(invoice.created_at),
        "stripe_hosted_url": invoice.stripe_hosted_url,
    }


def _pack_routes(pack_id: UUID) -> dict[str, str]:
    base = f"/packs/{pack_id}"
    return {
        "pack": base,
        "follow_up_queue": f"{base}?step=9",
        "leads": f"{base}/leads",
        "proposals": f"{base}/proposal",
        "invoices": f"{base}/invoice",
        "website": f"{base}/website",
        "brand_os": f"{base}/brand-os",
    }


def _task_counts(pending_tasks: list, overdue_tasks: list) -> dict[str, int]:
    now = _now()
    due_today = sum(1 for t in pending_tasks if t.due_date.date() == now.date() and t.due_date >= now)
    upcoming = sum(1 for t in pending_tasks if t.due_date.date() != now.date() and t.due_date >= now)
    return {
        "pending": len(pending_tasks),
        "overdue": len(overdue_tasks),
        "due_today": due_today,
        "upcoming": upcoming,
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
    revenue_limit: int = 20,
) -> dict:
    """Return a bounded snapshot of a single pack's execution state."""
    pack_uuid = _safe_uuid(pack_id)
    pack = db.query(Pack).filter(Pack.id == pack_uuid).first()
    if not pack:
        raise ValueError("Pack not found")

    lead_limit = _normalize_limit(lead_limit, default=20, maximum=50)
    task_limit = _normalize_limit(task_limit, default=20, maximum=50)
    revenue_limit = _normalize_limit(revenue_limit, default=20, maximum=50)

    brand_os = get_active_brand_os(db, pack_uuid)
    campaign = get_active_campaign(db, pack_uuid)
    sprint = get_active_sprint_for_pack(db, pack_uuid)

    published_site = get_published_for_pack(db, pack_uuid)
    draft_site = get_for_pack_any(db, pack_uuid)
    website_status = "none"
    if published_site:
        website_status = "published"
    elif draft_site:
        website_status = "draft"

    leads = list_leads_for_pack(db, pack_uuid)
    lead_items = leads[:lead_limit]
    lead_counts = {
        "total": len(leads),
        "new": sum(1 for l in leads if l.status == LEAD_STATUS_NEW),
        "qualified": sum(1 for l in leads if l.status == LEAD_STATUS_QUALIFIED),
    }
    for lead in leads:
        if lead.status:
            lead_counts[lead.status] = lead_counts.get(lead.status, 0) + 1

    pending_tasks = get_pending_tasks_sorted_for_queue(db, pack_uuid)
    overdue_tasks = get_overdue_tasks(db, pack_uuid)
    lead_name_map = {str(lead.id): lead.name for lead in leads}

    proposals = list_proposals_for_pack(db, pack_uuid)
    invoices = list_invoices_for_pack(db, pack_uuid)

    return {
        "scope": "pack",
        "pack": {
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
        "sprint": {
            "current_day": sprint.current_day if sprint else None,
            "mode": sprint.mode if sprint else None,
            "status": sprint.status if sprint else None,
        },
        "brand_os": {
            "active_version": brand_os.version if brand_os else None,
            "is_available": bool(brand_os),
        },
        "campaign": {
            "primary_cta": campaign.primary_cta if campaign else None,
            "goal": campaign.goal if campaign else None,
            "angles_count": len(campaign.angles or []) if campaign else 0,
            "is_available": bool(campaign),
        },
        "website": {
            "status": website_status,
            "live_url": published_site.live_url if published_site else None,
            "published_at": _iso(published_site.published_at) if published_site else None,
        },
        "leads": {
            "counts": lead_counts,
            "items": [_lead_payload(lead) for lead in lead_items],
        },
        "follow_up_queue": {
            "counts": _task_counts(pending_tasks, overdue_tasks),
            "items": [
                _task_payload(task, lead_name=lead_name_map.get(str(task.lead_id)))
                for task in pending_tasks[:task_limit]
            ],
        },
        "revenue": {
            "proposals": {
                "counts": _status_counts(proposals, ["draft", "sent", "accepted", "declined"]),
                "items": [_proposal_payload(item) for item in proposals[:revenue_limit]],
            },
            "invoices": {
                "counts": _status_counts(invoices, ["draft", "sent", "paid", "overdue"]),
                "items": [_invoice_payload(item) for item in invoices[:revenue_limit]],
            },
        },
        "routes": _pack_routes(pack_uuid),
    }


def get_pack_followup_queue(
    db: Session,
    pack_id: UUID | str,
    status: str = "pending",
    limit: int = 30,
) -> dict:
    """Return pending/overdue follow-up queue for a pack."""
    pack_uuid = _safe_uuid(pack_id)
    pack = db.query(Pack).filter(Pack.id == pack_uuid).first()
    if not pack:
        raise ValueError("Pack not found")

    limit = _normalize_limit(limit, default=30, maximum=100)
    status = (status or "pending").lower().strip()

    pending_tasks = get_pending_tasks_sorted_for_queue(db, pack_uuid)
    overdue_tasks = get_overdue_tasks(db, pack_uuid)
    selected = overdue_tasks if status == "overdue" else pending_tasks

    leads = list_leads_for_pack(db, pack_uuid)
    lead_name_map = {str(lead.id): lead.name for lead in leads}

    return {
        "scope": "pack",
        "pack": {"id": str(pack.id), "name": pack.name},
        "status": "overdue" if status == "overdue" else "pending",
        "counts": _task_counts(pending_tasks, overdue_tasks),
        "items": [
            _task_payload(task, lead_name=lead_name_map.get(str(task.lead_id)))
            for task in selected[:limit]
        ],
        "routes": _pack_routes(pack_uuid),
    }


def get_account_snapshot(
    db: Session,
    user_id: UUID | str,
    pack_limit: int = 20,
    task_limit: int = 30,
    include_archived: bool = False,
) -> dict:
    """Return account-wide summary across the user's packs."""
    user_uuid = _safe_uuid(user_id)
    pack_limit = _normalize_limit(pack_limit, default=20, maximum=50)
    task_limit = _normalize_limit(task_limit, default=30, maximum=100)

    packs = list_packs_for_user(db, user_uuid, include_archived=include_archived)
    selected_packs = packs[:pack_limit]

    account_pending = 0
    account_overdue = 0
    account_leads = 0
    account_proposals = 0
    account_invoices = 0
    overdue_items: list[dict] = []
    pack_rows: list[dict] = []

    for pack in selected_packs:
        leads = list_leads_for_pack(db, pack.id)
        proposals = list_proposals_for_pack(db, pack.id)
        invoices = list_invoices_for_pack(db, pack.id)
        pending_tasks = get_pending_tasks_sorted_for_queue(db, pack.id)
        overdue_tasks = get_overdue_tasks(db, pack.id)
        sprint = get_active_sprint_for_pack(db, pack.id)

        account_leads += len(leads)
        account_proposals += len(proposals)
        account_invoices += len(invoices)
        account_pending += len(pending_tasks)
        account_overdue += len(overdue_tasks)

        lead_new = sum(1 for l in leads if l.status == LEAD_STATUS_NEW)
        lead_qualified = sum(1 for l in leads if l.status == LEAD_STATUS_QUALIFIED)

        pack_rows.append(
            {
                "pack_id": str(pack.id),
                "pack_name": pack.name,
                "pack_status": pack.status,
                "current_day": sprint.current_day if sprint else None,
                "leads": {
                    "total": len(leads),
                    "new": lead_new,
                    "qualified": lead_qualified,
                },
                "follow_up": {
                    "pending": len(pending_tasks),
                    "overdue": len(overdue_tasks),
                },
                "proposals": _status_counts(proposals, ["draft", "sent", "accepted", "declined"]),
                "invoices": _status_counts(invoices, ["draft", "sent", "paid", "overdue"]),
                "routes": _pack_routes(pack.id),
            }
        )

        lead_name_map = {str(lead.id): lead.name for lead in leads}
        for task in overdue_tasks:
            overdue_items.append(
                {
                    **_task_payload(task, lead_name=lead_name_map.get(str(task.lead_id))),
                    "pack_name": pack.name,
                    "pack_route": f"/packs/{pack.id}",
                }
            )

    overdue_items.sort(key=lambda t: t.get("due_date") or "")

    return {
        "scope": "account",
        "packs_total": len(packs),
        "packs_returned": len(selected_packs),
        "totals": {
            "leads": account_leads,
            "follow_up_pending": account_pending,
            "follow_up_overdue": account_overdue,
            "proposals": account_proposals,
            "invoices": account_invoices,
        },
        "overdue_follow_ups": overdue_items[:task_limit],
        "packs": pack_rows,
        "routes": {"packs": "/packs"},
    }
