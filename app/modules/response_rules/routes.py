"""Response rules API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.modules.response_rules import services


router = APIRouter(prefix="/api/v1/response-rules", tags=["response-rules"])


class ResponseRuleRead(BaseModel):
    id: UUID
    pack_id: UUID
    trigger: str
    response_template: str
    locked_at: datetime | None
    
    class Config:
        from_attributes = True


class UpdateRuleRequest(BaseModel):
    response_template: str


@router.get("", response_model=list[ResponseRuleRead])
def get_rules(
    pack_id: UUID = Query(...),
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all response rules for a pack."""
    rules = services.get_response_rules(db, pack_id)
    return rules


@router.post("/generate", response_model=list[ResponseRuleRead])
def generate_rules(
    pack_id: UUID = Query(...),
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate default response rules for a pack."""
    rules = services.generate_response_rules(db, pack_id)
    return rules


@router.patch("/{rule_id}", response_model=ResponseRuleRead)
def update_rule(
    rule_id: UUID,
    request: UpdateRuleRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a response rule."""
    rule = services.update_response_rule(db, rule_id, request.response_template)
    return rule


@router.post("/lock", response_model=list[ResponseRuleRead])
def lock_rules(
    pack_id: UUID = Query(...),
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lock all response rules for a pack (Day 8)."""
    rules = services.lock_response_rules(db, pack_id)
    return rules
