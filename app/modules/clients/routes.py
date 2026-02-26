"""Clients and Leads API. Clients CRUD; Leads CRUD and qualify (pack-scoped)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import NotFoundError
from app.modules.packs.models import User
from app.modules.packs.services import get_pack_for_user
from app.modules.clients.schemas import (
    ClientCreate,
    ClientList,
    ClientRead,
    ClientUpdate,
    LeadCreate,
    LeadList,
    LeadRead,
    LeadUpdate,
)
from app.modules.clients.services import (
    list_for_user,
    get_for_user,
    create,
    update,
    delete,
    list_leads_for_pack,
    list_qualified_leads_for_pack,
    get_lead_for_pack_user,
    create_lead,
    update_lead,
    qualify_lead,
)

router = APIRouter()


@router.get("", response_model=ClientList)
def list_clients(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List clients for the authenticated user."""
    items = list_for_user(db, current_user.id)
    return ClientList(items=[ClientRead.model_validate(c) for c in items], total=len(items))


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    body: ClientCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a client."""
    client = create(db, current_user.id, body.name, body.email, body.company)
    return ClientRead.model_validate(client)


# --- Leads (pack-scoped; must be before /{client_id}) ---

def _ensure_pack_access(db, pack_id: UUID, user_id: UUID) -> None:
    if not get_pack_for_user(db, pack_id, user_id):
        raise NotFoundError("Pack not found")


@router.get("/leads", response_model=LeadList)
def list_leads(
    pack_id: UUID = Query(..., description="Pack id"),
    qualified_only: bool = Query(False, description="If true, return only qualified leads"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List leads for a pack. Pack must belong to current user."""
    _ensure_pack_access(db, pack_id, current_user.id)
    if qualified_only:
        items = list_qualified_leads_for_pack(db, pack_id)
    else:
        items = list_leads_for_pack(db, pack_id)
    return LeadList(items=[LeadRead.model_validate(l) for l in items], total=len(items))


@router.post("/leads", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead_route(
    body: LeadCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a lead for a pack. Pack must belong to current user."""
    _ensure_pack_access(db, body.pack_id, current_user.id)
    if body.client_id:
        if not get_for_user(db, body.client_id, current_user.id):
            raise NotFoundError("Client not found")
    lead = create_lead(
        db,
        pack_id=body.pack_id,
        name=body.name,
        phone=body.phone,
        email=body.email,
        source=body.source,
        summary=body.summary,
        budget_range=body.budget_range,
        urgency=body.urgency,
        client_id=body.client_id,
        pipeline_stage=body.pipeline_stage,
        due_date=body.due_date,
        deal_value=body.deal_value,
        assigned_user_id=body.assigned_user_id,
    )
    try:
        from app.modules.tasks.services import create_new_lead_followup_tasks
        create_new_lead_followup_tasks(db, pack_id=body.pack_id, lead_id=lead.id, lead_name=lead.name or "Lead")
    except Exception:
        pass  # Don't fail lead creation if task creation fails
    return LeadRead.model_validate(lead)


@router.get("/leads/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a lead by id. Lead's pack must belong to current user."""
    lead = get_lead_for_pack_user(db, lead_id, current_user.id)
    if not lead:
        raise NotFoundError("Lead not found")
    return LeadRead.model_validate(lead)


@router.patch("/leads/{lead_id}", response_model=LeadRead)
def update_lead_route(
    lead_id: UUID,
    body: LeadUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a lead."""
    lead = get_lead_for_pack_user(db, lead_id, current_user.id)
    if not lead:
        raise NotFoundError("Lead not found")
    if body.client_id is not None and body.client_id:
        if not get_for_user(db, body.client_id, current_user.id):
            raise NotFoundError("Client not found")
    data = body.model_dump(exclude_unset=True)
    lead = update_lead(db, lead, **data)
    # Auto-close pending follow-up tasks when lead becomes booked/won/lost
    from app.modules.clients.models import LEAD_STATUS_CONVERTED, LEAD_STATUS_DISQUALIFIED, PIPELINE_STAGE_CLOSED
    from app.modules.tasks.services import close_pending_tasks_for_lead
    if lead.status in (LEAD_STATUS_CONVERTED, LEAD_STATUS_DISQUALIFIED) or lead.pipeline_stage == PIPELINE_STAGE_CLOSED:
        try:
            close_pending_tasks_for_lead(db, lead.id)
        except Exception:
            pass
    return LeadRead.model_validate(lead)


@router.post("/leads/{lead_id}/qualify", response_model=LeadRead)
def qualify_lead_route(
    lead_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a lead as qualified (for proposal gate)."""
    lead = get_lead_for_pack_user(db, lead_id, current_user.id)
    if not lead:
        raise NotFoundError("Lead not found")
    lead = qualify_lead(db, lead)
    return LeadRead.model_validate(lead)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a client by id."""
    client = get_for_user(db, client_id, current_user.id)
    if not client:
        raise NotFoundError("Client not found")
    return ClientRead.model_validate(client)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: UUID,
    body: ClientUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a client."""
    client = get_for_user(db, client_id, current_user.id)
    if not client:
        raise NotFoundError("Client not found")
    data = body.model_dump(exclude_unset=True)
    client = update(db, client, **data)
    return ClientRead.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a client."""
    client = get_for_user(db, client_id, current_user.id)
    if not client:
        raise NotFoundError("Client not found")
    delete(db, client)
