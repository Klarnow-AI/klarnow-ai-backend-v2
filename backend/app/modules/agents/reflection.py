"""Reflection triggers (Phase 7 stub). Emit trigger events to decision log for later reflection flow."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.agents.models import DecisionLog

TRIGGER_WEEKLY_CHECKPOINT = "weekly_checkpoint"
TRIGGER_CTA_CHANGE = "cta_change"
TRIGGER_PLAN_HORIZON_UNLOCK = "plan_horizon_unlock"
TRIGGER_MANUAL = "manual"


def emit_reflection_trigger(
    db: Session,
    pack_id: UUID,
    trigger_type: str,
    payload: dict | None = None,
) -> None:
    """Log a reflection trigger for the pack. No auto-activation; for observability and future reflection flow."""
    db.add(
        DecisionLog(
            tool_name="reflection_trigger",
            agent="system",
            pack_id=pack_id,
            inputs_sanitized={"trigger": trigger_type, "payload": payload or {}},
            success=True,
            result_summary=None,
        )
    )
    db.commit()
