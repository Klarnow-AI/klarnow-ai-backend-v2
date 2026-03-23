"""Template library for follow-up tasks. Per Follow-up MVP Spec."""

from app.modules.tasks.models import (
    TEMPLATE_KEY_FOLLOWUP_2H,
    TEMPLATE_KEY_FOLLOWUP_24H,
    TEMPLATE_KEY_FOLLOWUP_72H,
    TEMPLATE_KEY_PROPOSAL_FOLLOWUP,
    TEMPLATE_KEY_INVOICE_CHASE,
)

FOLLOWUP_TEMPLATES = {
    TEMPLATE_KEY_FOLLOWUP_2H: "Hey — just checking you saw the details I sent earlier. Happy to answer questions.",
    TEMPLATE_KEY_FOLLOWUP_24H: "Quick nudge in case this got buried. Want me to hold a spot for you?",
    TEMPLATE_KEY_FOLLOWUP_72H: "Last check from me — should I close this for now?",
    TEMPLATE_KEY_PROPOSAL_FOLLOWUP: "Just checking if you had time to review the proposal. Happy to walk through it.",
    TEMPLATE_KEY_INVOICE_CHASE: "Quick reminder about the invoice. Let me know if you need anything from me.",
}


def get_template(template_key: str) -> str:
    """Return message template by key. Raises KeyError if unknown."""
    return FOLLOWUP_TEMPLATES[template_key]
