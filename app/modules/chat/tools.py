"""Chat tools: ask_day_question for Day 0-3 conversational flow."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.sprint.day_definitions import get_step_by_field_key
from app.modules.sprint.suggestions import suggest_day_field_chips

ASK_DAY_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "pack_id": {"type": "string", "format": "uuid", "description": "Pack id"},
        "field_key": {
            "type": "string",
            "description": "The field key for the current question (e.g. brand_name, primary_cta, usp_category, offer_one_liner)",
        },
        "day_context": {
            "type": "integer",
            "description": "Current day (0, 1, 2, or 3) from pack context",
        },
        "re_suggest": {
            "type": "boolean",
            "description": "If true, user asked for different suggestions; exclude previous chips",
            "default": False,
        },
        "previous_chips": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Labels of chips user already saw (for re_suggest)",
        },
    },
    "required": ["pack_id", "field_key", "day_context"],
}


def ask_day_question(
    db: Session,
    pack_id: UUID | str,
    field_key: str,
    day_context: int,
    re_suggest: bool = False,
    previous_chips: list[str] | None = None,
    **kwargs: object,
) -> dict:
    """
    Return input metadata and suggestion chips for a Day 0-3 question.
    Call this when asking a question so the user gets placeholder, input type, and chips.
    """
    if isinstance(pack_id, str):
        pack_id = UUID(pack_id)

    step = get_step_by_field_key(day_context, field_key)
    if not step:
        return {
            "field_key": field_key,
            "input_placeholder": None,
            "input_type": "input",
            "suggestion_chips": [],
            "show_resuggest": False,
        }

    input_placeholder = step.get("placeholder")
    input_type = step.get("input_type", "input")

    exclude = list(previous_chips or []) if re_suggest else None
    chips = suggest_day_field_chips(
        db, pack_id, day_context, field_key, count=4, exclude=exclude
    )

    # show_resuggest: true for LLM-generated chips; false for static options only
    options = step.get("options")
    show_resuggest = bool(chips) and (options is None or re_suggest)

    return {
        "field_key": field_key,
        "input_placeholder": input_placeholder,
        "input_type": input_type,
        "suggestion_chips": chips,
        "show_resuggest": show_resuggest,
    }
