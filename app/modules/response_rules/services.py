"""Response rules service."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_service_action
from app.modules.response_rules.models import (
    TRIGGER_BOOKING_REQUEST,
    TRIGGER_COMPARISON_OBJECTION,
    TRIGGER_INITIAL_ENQUIRY,
    TRIGGER_PRICE_OBJECTION,
    TRIGGER_TIMING_OBJECTION,
    ResponseRule,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


RESPONSE_TEMPLATES = {
    TRIGGER_INITIAL_ENQUIRY: "Hey [Name]! Thanks for reaching out. I help [who] with [what]. Are you looking to [CTA]? If so, [next step].",
    TRIGGER_PRICE_OBJECTION: "I hear you. What most people find is that [value statement]. For example, [evidence]. Does that make sense?",
    TRIGGER_TIMING_OBJECTION: "Totally understand. When's the right time for you? I can [flexibility offer]. Would that work?",
    TRIGGER_COMPARISON_OBJECTION: "Great question. The main difference is [unique approach]. That means [specific benefit]. Sound like what you need?",
    TRIGGER_BOOKING_REQUEST: "Perfect! Here's my calendar: [link]. Pick a time that works for you and we'll take it from there.",
}


@log_service_action()
def generate_response_rules(db: Session, pack_id: UUID) -> list[ResponseRule]:
    """Generate default response rules for a pack."""
    rules = []
    
    for trigger, template in RESPONSE_TEMPLATES.items():
        rule = ResponseRule(
            pack_id=pack_id,
            trigger=trigger,
            response_template=template,
        )
        db.add(rule)
        rules.append(rule)
    
    db.commit()
    for rule in rules:
        db.refresh(rule)
    
    return rules


@log_service_action()
def get_response_rules(db: Session, pack_id: UUID) -> list[ResponseRule]:
    """Get all response rules for a pack."""
    return db.query(ResponseRule).filter(ResponseRule.pack_id == pack_id).all()


@log_service_action()
def update_response_rule(db: Session, rule_id: UUID, response_template: str) -> ResponseRule:
    """Update a response rule template."""
    rule = db.query(ResponseRule).filter(ResponseRule.id == rule_id).first()
    if not rule:
        raise ValueError(f"Rule {rule_id} not found")
    
    if rule.locked_at:
        raise ValueError("Cannot update locked rule")
    
    rule.response_template = response_template
    db.commit()
    db.refresh(rule)
    return rule


@log_service_action()
def lock_response_rules(db: Session, pack_id: UUID) -> list[ResponseRule]:
    """Lock all response rules for a pack (Day 8)."""
    rules = get_response_rules(db, pack_id)
    
    if not rules:
        raise ValueError("No response rules found. Generate them first.")
    
    now = utc_now()
    for rule in rules:
        rule.locked_at = now
    
    db.commit()
    for rule in rules:
        db.refresh(rule)
    
    return rules


@log_service_action()
def are_rules_locked(db: Session, pack_id: UUID) -> bool:
    """Check if response rules are locked for a pack."""
    rules = get_response_rules(db, pack_id)
    if not rules:
        return False
    return all(rule.locked_at is not None for rule in rules)
