"""Ad Factory Pattern Registry. Deterministic selection only."""

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

LINE_TEMPLATES = {
    "problem_1": "You're stuck with [pain].",
    "problem_2": "Most people struggle with [pain] every day.",
    "problem_3": "[Pain] is costing you [outcome].",
    "mechanism_1": "We do [mechanism] so you get [outcome].",
    "mechanism_2": "Our process delivers [outcome] without [pain].",
    "mechanism_3": "[Differentiator] means you get [outcome] faster.",
    "offer_1": "Get started today.",
    "offer_2": "Limited spots available.",
    "offer_3": "Join [X] others who've already [outcome].",
}

CTA_TEMPLATES = {
    "book_cta": {"action": "book", "mid": "Book your call now", "end": "Book your call in the link below"},
    "call_cta": {"action": "call", "mid": "Call us today", "end": "Call the number below"},
    "dm_cta": {"action": "dm", "mid": "DM me to get started", "end": "Slide into my DMs"},
    "visit_cta": {"action": "visit", "mid": "Visit the link below", "end": "Click the link in bio"},
    "buy_cta": {"action": "buy", "mid": "Get it now", "end": "Add to cart in the link"},
    "whatsapp_cta": {"action": "whatsapp", "mid": "Message us on WhatsApp", "end": "WhatsApp the link below"},
    "apply_cta": {"action": "apply", "mid": "Apply now", "end": "Apply in the link below"},
}

HOOK_TEMPLATES = {
    "question_1": "What if you could [outcome] without [pain]?",
    "question_2": "Tired of [pain]?",
    "question_3": "Ready to [outcome]?",
    "bold_claim_1": "The fastest way to [outcome].",
    "bold_claim_2": "[X] people have already [outcome].",
    "bold_claim_3": "Stop [pain]. Start [outcome].",
    "relatable_moment_1": "I used to [pain] too.",
    "relatable_moment_2": "Sound familiar? [pain] every single day.",
    "contrarian_truth_1": "Most [audience] get [pain] wrong.",
    "stop_doing_this_1": "Stop [common mistake].",
}

PATTERNS = {
    "pattern_001": {"path": "pain_escape"},
    "pattern_002": {"path": "status_upgrade"},
    "pattern_003": {"path": "convenience"},
    "pattern_004": {"path": "trust_safety"},
    "pattern_005": {"path": "transformation"},
}

BEAT_BLUEPRINT_STANDARD = ["hook", "problem", "mechanism", "proof", "offer", "cta"]
BEAT_BLUEPRINT_OFFER_SMASH = ["hook", "offer", "problem", "mechanism", "proof", "cta"]


def get_pattern_for_path(path: str) -> str:
    for pid, p in PATTERNS.items():
        if p["path"] == path:
            return pid
    return list(PATTERNS.keys())[0]


def get_hook_template(hook_type: str, slot: str) -> str:
    key = f"{hook_type}_{((hash(slot) % 3) + 1)}"
    return HOOK_TEMPLATES.get(key, HOOK_TEMPLATES["question_1"])
