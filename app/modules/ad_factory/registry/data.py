"""Deterministic pattern registry for Ad Factory V2.1."""

from __future__ import annotations

import hashlib
from typing import Any, Literal


REGISTRY_VERSION = "2026.03.12"
PATTERN_PACK_VERSION = "v2.1"
ENGINE_LOGIC_VERSION = "2026.03.12.1"
PROVIDER_ADAPTER_VERSION = "kling-adapter-1"
SCHEMA_VERSION = "ad-factory-v2.1"

PATHS = ["pain_escape", "status_upgrade", "convenience", "trust_safety", "transformation"]
TREATMENTS = [
    "talking_head_authority",
    "cinematic_process",
    "ugc_customer_story",
    "offer_smash",
]
HOOK_TYPES = [
    "question",
    "bold_claim",
    "relatable_moment",
    "before_after_tease",
    "contrarian_truth",
    "stop_doing_this",
]
INTENT_MAP = {"A": "emotion_led", "B": "logic_led", "C": "offer_led"}
VARIANT_C_TREATMENT = "offer_smash"

RegistryItemType = Literal[
    "pattern",
    "hook",
    "line_template",
    "proof_strategy",
    "cta",
    "beat_blueprint",
]


def _stable_hash(*parts: object) -> int:
    joined = "::".join(str(part) for part in parts)
    return int(hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12], 16)


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _make_item(
    item_id: str,
    item_type: RegistryItemType,
    **data: Any,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "item_type": item_type,
        "registry_version": REGISTRY_VERSION,
        "pattern_pack_version": PATTERN_PACK_VERSION,
        "deprecated": False,
        **data,
    }


PATTERNS: dict[str, dict[str, Any]] = {}
for path_index, path in enumerate(PATHS, start=1):
    for variant_index, objective in enumerate(["lead_gen", "booking", "purchase", "lead_gen", "lead_gen"], start=1):
        item_id = f"pattern_{path_index:02d}_{variant_index:02d}"
        PATTERNS[item_id] = _make_item(
            item_id,
            "pattern",
            path=path,
            allowed_objectives=[objective],
            allowed_treatments=TREATMENTS,
            allowed_traffic_sources=["unknown", "organic", "meta", "tiktok", "search"],
        )


_HOOK_TEMPLATES_BY_TYPE = {
    "question": [
        "What if you could [outcome] without [pain]?",
        "Why are [audience] still putting up with [pain]?",
        "What would change if [outcome] felt simple?",
        "How much longer can [pain] keep stealing your momentum?",
        "What if [audience] had a cleaner path to [outcome]?",
        "Could [outcome] happen faster than you think?",
        "Why does [pain] still feel normal in your market?",
        "What would it take to make [outcome] repeatable?",
        "Are you still settling for [pain] as the default?",
    ],
    "bold_claim": [
        "The clearest route to [outcome] starts here.",
        "A stronger way to get [outcome] without the usual drag.",
        "This is how [audience] move faster toward [outcome].",
        "A premium shortcut to [outcome] starts with one change.",
        "You can turn [pain] into [outcome] with the right system.",
        "The sharper play for [outcome] is already available.",
        "This process makes [outcome] easier to believe.",
        "A more reliable route to [outcome] is on the table.",
        "You do not need more chaos to get [outcome].",
    ],
    "relatable_moment": [
        "You open your day and [pain] is already waiting.",
        "You try again, and [pain] shows up in the same place.",
        "You know that moment when [pain] ruins the next step?",
        "It starts small, then [pain] eats the whole afternoon.",
        "That familiar cycle of [pain] should not be your normal.",
        "The worst part of [pain] is how quickly it drains momentum.",
        "You thought this week would be different, then [pain] appeared.",
        "It is exhausting when [pain] keeps resetting your progress.",
    ],
    "before_after_tease": [
        "Before: [pain]. After: [outcome].",
        "From [pain] to [outcome] without guesswork.",
        "Watch [audience] move from [pain] to [outcome].",
        "One system can turn [pain] into [outcome].",
        "You can feel the gap between [pain] and [outcome].",
        "This is the shift from [pain] to [outcome].",
        "The move from [pain] to [outcome] is smaller than it looks.",
        "A simple transition from [pain] into [outcome].",
    ],
    "contrarian_truth": [
        "Most people chase [outcome] by doubling down on the wrong thing.",
        "The usual advice around [pain] keeps people stuck.",
        "More effort is not the fix for [pain].",
        "The loudest strategy for [outcome] is rarely the best one.",
        "The default playbook for [audience] makes [pain] worse.",
        "You do not need another hack to reach [outcome].",
        "Most [audience] are solving the wrong problem first.",
        "The old way to chase [outcome] is costing too much.",
    ],
    "stop_doing_this": [
        "Stop letting [pain] set the pace.",
        "Stop gambling on [pain] fixing itself.",
        "Stop treating [pain] like a strategy.",
        "Stop waiting for [outcome] to appear on its own.",
        "Stop buying more complexity than [audience] need.",
        "Stop repeating the same move that creates [pain].",
        "Stop forcing [outcome] through a broken process.",
        "Stop making [pain] the price of growth.",
    ],
}

HOOKS: dict[str, dict[str, Any]] = {}
for hook_type, templates in _HOOK_TEMPLATES_BY_TYPE.items():
    for index, template in enumerate(templates, start=1):
        item_id = f"hook_{hook_type}_{index:02d}"
        HOOKS[item_id] = _make_item(
            item_id,
            "hook",
            hook_type=hook_type,
            template=template,
            allowed_objectives=["lead_gen", "booking", "purchase"],
            allowed_treatments=TREATMENTS,
            allowed_traffic_sources=["unknown", "organic", "meta", "tiktok", "search"],
        )


_LINE_TEMPLATE_CATEGORIES = {
    "problem": [
        "Right now [audience] are stuck with [pain].",
        "Most [audience] lose time to [pain] before anything improves.",
        "[Pain] keeps blocking the result they actually want.",
        "The usual way of handling [pain] drains energy and trust.",
        "Every extra week of [pain] delays [outcome].",
        "[Pain] makes growth feel heavier than it should.",
        "Without a clear system, [pain] keeps repeating.",
        "Too many [audience] accept [pain] as normal.",
        "What looks manageable now becomes expensive when [pain] sticks around.",
        "[Pain] keeps people close to the same ceiling.",
        "A messy response to [pain] creates even more friction.",
        "[Pain] keeps turning simple work into slow work.",
        "The longer [pain] stays unchallenged, the harder [outcome] feels.",
        "[Pain] is costing more momentum than it first appears.",
        "Small moments of [pain] become big bottlenecks quickly.",
        "This is what [pain] looks like in real life for [audience].",
        "The hidden cost of [pain] is how it delays [outcome].",
        "When [pain] becomes routine, progress gets quieter.",
        "Most teams underestimate how much [pain] compounds.",
        "[Pain] is the pattern that keeps repeating until the system changes.",
    ],
    "mechanism": [
        "We do [mechanism] so you get [outcome].",
        "We do [mechanism] so [audience] can reach [outcome].",
        "We do [mechanism] so you move from [pain] to [outcome].",
        "We do [mechanism] so your next step toward [outcome] is clearer.",
        "We do [mechanism] so the shift away from [pain] becomes practical.",
        "We do [mechanism] so [outcome] stops feeling vague.",
        "We do [mechanism] so [audience] can build [outcome] faster.",
        "We do [mechanism] so progress toward [outcome] becomes visible.",
        "We do [mechanism] so you keep momentum toward [outcome].",
        "We do [mechanism] so [pain] no longer drives the process.",
        "We do [mechanism] so [audience] can trade friction for [outcome].",
        "We do [mechanism] so [outcome] becomes repeatable.",
        "We do [mechanism] so the path to [outcome] stays focused.",
        "We do [mechanism] so your effort compounds toward [outcome].",
        "We do [mechanism] so [audience] can trust the process again.",
        "We do [mechanism] so [outcome] happens with less drag.",
        "We do [mechanism] so [pain] stops hijacking the timeline.",
        "We do [mechanism] so the results line up with the effort.",
        "We do [mechanism] so [outcome] feels realistic and measurable.",
        "We do [mechanism] so [audience] can move with more confidence.",
    ],
    "offer": [
        "Start with [offer] and move toward [outcome].",
        "Take the next step with [offer].",
        "Use [offer] to make [outcome] easier to reach.",
        "Choose [offer] when you want a clearer route to [outcome].",
        "Make [offer] the move that replaces [pain].",
        "Use [offer] to build momentum toward [outcome].",
        "Let [offer] turn the next step into visible progress.",
        "Take [offer] and bring structure to the process.",
        "Start [offer] now so the gap to [outcome] gets smaller.",
        "Use [offer] to put a better system in place.",
        "Make room for [offer] if [pain] has gone on too long.",
        "Try [offer] when you want the process to feel sharper.",
        "Use [offer] to remove friction and protect progress.",
        "Choose [offer] if you want [outcome] with less noise.",
        "Begin with [offer] and make [outcome] easier to see.",
        "Use [offer] to replace guesswork with structure.",
        "Take [offer] and build a more reliable route forward.",
        "Start [offer] if [audience] are ready to move faster.",
        "Use [offer] to make progress feel grounded.",
        "Choose [offer] before another cycle of [pain] repeats.",
    ],
}

LINE_TEMPLATES: dict[str, dict[str, Any]] = {}
for category, templates in _LINE_TEMPLATE_CATEGORIES.items():
    for index, template in enumerate(templates, start=1):
        item_id = f"line_{category}_{index:02d}"
        LINE_TEMPLATES[item_id] = _make_item(
            item_id,
            "line_template",
            category=category,
            template=template,
            allowed_objectives=["lead_gen", "booking", "purchase"],
            allowed_treatments=TREATMENTS,
            allowed_traffic_sources=["unknown", "organic", "meta", "tiktok", "search"],
        )


PROOF_STRATEGIES: dict[str, dict[str, Any]] = {
    "proof_testimonial_lead": _make_item(
        "proof_testimonial_lead",
        "proof_strategy",
        fallback_used=False,
        label="Lead with testimonial proof",
    ),
    "proof_numbers_lead": _make_item(
        "proof_numbers_lead",
        "proof_strategy",
        fallback_used=False,
        label="Lead with measurable results",
    ),
    "proof_case_study": _make_item(
        "proof_case_study",
        "proof_strategy",
        fallback_used=False,
        label="Lead with mini case study",
    ),
    "proof_screenshot": _make_item(
        "proof_screenshot",
        "proof_strategy",
        fallback_used=False,
        label="Lead with screenshot proof",
    ),
    "proof_before_after": _make_item(
        "proof_before_after",
        "proof_strategy",
        fallback_used=False,
        label="Lead with before and after framing",
    ),
    "proof_press": _make_item(
        "proof_press",
        "proof_strategy",
        fallback_used=False,
        label="Lead with press or certification proof",
    ),
    "proof_ugc": _make_item(
        "proof_ugc",
        "proof_strategy",
        fallback_used=False,
        label="Lead with UGC style proof",
    ),
    "proof_fallback_generic": _make_item(
        "proof_fallback_generic",
        "proof_strategy",
        fallback_used=True,
        label="Fallback generic proof",
    ),
}


CTA_TEMPLATES: dict[str, dict[str, Any]] = {
    "cta_book": _make_item("cta_book", "cta", action="book", mid="Book your next step now.", end="Book through the link below."),
    "cta_call": _make_item("cta_call", "cta", action="call", mid="Call now to get started.", end="Call the number below."),
    "cta_dm": _make_item("cta_dm", "cta", action="dm", mid="Send a DM to get started.", end="DM now to take the next step."),
    "cta_visit": _make_item("cta_visit", "cta", action="visit", mid="Visit the link now.", end="Use the link below to continue."),
    "cta_buy": _make_item("cta_buy", "cta", action="buy", mid="Buy now and lock it in.", end="Buy from the link below."),
    "cta_whatsapp": _make_item("cta_whatsapp", "cta", action="whatsapp", mid="Message us on WhatsApp now.", end="Open WhatsApp from the link below."),
    "cta_apply": _make_item("cta_apply", "cta", action="apply", mid="Apply now to move forward.", end="Apply through the link below."),
    "cta_book_consult": _make_item("cta_book_consult", "cta", action="book", mid="Book your consult now.", end="Book your consult in the link below."),
    "cta_buy_offer": _make_item("cta_buy_offer", "cta", action="buy", mid="Get the offer today.", end="Claim it from the link below."),
    "cta_visit_profile": _make_item("cta_visit_profile", "cta", action="visit", mid="Open the profile link now.", end="Tap the link in bio now."),
}


BEAT_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "beat_blueprint_standard": _make_item(
        "beat_blueprint_standard",
        "beat_blueprint",
        beats=["hook", "problem", "mechanism", "proof", "offer", "cta"],
    ),
    "beat_blueprint_offer_smash": _make_item(
        "beat_blueprint_offer_smash",
        "beat_blueprint",
        beats=["hook", "offer", "problem", "mechanism", "proof", "cta"],
    ),
}


def _eligible(
    item: dict[str, Any],
    *,
    objective_type: str,
    treatment: str | None = None,
    traffic_source: str | None = None,
) -> bool:
    if item.get("deprecated"):
        return False
    if objective_type and objective_type not in item.get("allowed_objectives", [objective_type]):
        return False
    if treatment and treatment not in item.get("allowed_treatments", [treatment]):
        return False
    if traffic_source and traffic_source not in item.get("allowed_traffic_sources", [traffic_source]):
        return False
    return True


def _pick_one(items: list[dict[str, Any]], *seed_parts: object) -> dict[str, Any]:
    if not items:
        raise ValueError("No eligible registry items found")
    index = _stable_hash(*seed_parts) % len(items)
    return items[index]


def list_patterns_for_path(path: str, *, objective_type: str, treatment: str, traffic_source: str) -> list[dict[str, Any]]:
    return [
        pattern
        for pattern in PATTERNS.values()
        if pattern["path"] == path
        and _eligible(
            pattern,
            objective_type=objective_type,
            treatment=treatment,
            traffic_source=traffic_source,
        )
    ]


def get_pattern_for_path(
    path: str,
    *,
    objective_type: str,
    treatment: str,
    traffic_source: str,
    selection_seed: str,
    slot: str,
) -> dict[str, Any]:
    items = list_patterns_for_path(
        path,
        objective_type=objective_type,
        treatment=treatment,
        traffic_source=traffic_source,
    )
    return _pick_one(items, "pattern", REGISTRY_VERSION, PATTERN_PACK_VERSION, selection_seed, slot, path)


def get_hook_template(
    hook_type: str,
    *,
    objective_type: str,
    treatment: str,
    traffic_source: str,
    selection_seed: str,
    slot: str,
) -> dict[str, Any]:
    items = [
        item
        for item in HOOKS.values()
        if item["hook_type"] == hook_type
        and _eligible(
            item,
            objective_type=objective_type,
            treatment=treatment,
            traffic_source=traffic_source,
        )
    ]
    return _pick_one(items, "hook", REGISTRY_VERSION, selection_seed, slot, hook_type)


def get_line_templates(
    category: str,
    *,
    objective_type: str,
    treatment: str,
    traffic_source: str,
    selection_seed: str,
    slot: str,
    count: int,
) -> list[dict[str, Any]]:
    items = [
        item
        for item in LINE_TEMPLATES.values()
        if item["category"] == category
        and _eligible(
            item,
            objective_type=objective_type,
            treatment=treatment,
            traffic_source=traffic_source,
        )
    ]
    if count <= 0:
        return []
    start = _stable_hash("line", REGISTRY_VERSION, selection_seed, slot, category) % len(items)
    selected: list[dict[str, Any]] = []
    for offset in range(count):
        selected.append(items[(start + offset) % len(items)])
    return selected


def get_cta_template(action: str, *, selection_seed: str, slot: str) -> dict[str, Any]:
    items = [
        item
        for item in CTA_TEMPLATES.values()
        if item["action"] == action
    ]
    return _pick_one(items, "cta", REGISTRY_VERSION, selection_seed, slot, action)


def get_proof_strategy(has_proof_assets: bool, *, selection_seed: str) -> dict[str, Any]:
    preferred = "proof_testimonial_lead" if has_proof_assets else "proof_fallback_generic"
    if preferred in PROOF_STRATEGIES:
        return PROOF_STRATEGIES[preferred]
    items = list(PROOF_STRATEGIES.values())
    return _pick_one(items, "proof_strategy", REGISTRY_VERSION, selection_seed, has_proof_assets)


def get_beat_blueprint(treatment: str) -> dict[str, Any]:
    if treatment == VARIANT_C_TREATMENT:
        return BEAT_BLUEPRINTS["beat_blueprint_offer_smash"]
    return BEAT_BLUEPRINTS["beat_blueprint_standard"]


def get_versions() -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "registry_version": REGISTRY_VERSION,
        "pattern_pack_version": PATTERN_PACK_VERSION,
        "engine_logic_version": ENGINE_LOGIC_VERSION,
        "provider_adapter_version": PROVIDER_ADAPTER_VERSION,
    }
