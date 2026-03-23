"""Provider adapter translating provider-neutral render intent into Kling requests."""

from __future__ import annotations

from app.modules.ad_factory.schemas import ProviderNeutralRenderIntent


def _clip(text: str | None, limit: int) -> str:
    return " ".join((text or "").split())[:limit]


def build_kling_prompt(intent: ProviderNeutralRenderIntent) -> str:
    anchor_descriptions = "; ".join(
        _clip(frame.description, 180) for frame in intent.anchor_frames
    )
    caption_lines = " | ".join(_clip(line, 60) for line in intent.caption_lines)
    parts = [
        f"Create a vertical 9:16 short-form video ad for {intent.business_name}.",
        f"Promote {intent.offer} to {intent.audience}.",
        f"Address the real pain around {intent.primary_pain}." if intent.primary_pain else "",
        f"Keep the concept centered on {intent.core_concept}.",
        f"Open with the spoken hook: '{intent.hook_line}'.",
        f"Use treatment: {intent.treatment}.",
        f"Brand context: {intent.brand_context_summary}." if intent.brand_context_summary else "",
        f"Art direction: {intent.visual_direction}." if intent.visual_direction else "",
        f"Visual sequence: {anchor_descriptions}.",
        "Audio must be present: use clear English narration plus subtle ambient sound, and do not return a silent render.",
        f"Narration should say exactly: {intent.spoken_narration}.",
        f"On-screen text should use lines like: {caption_lines}.",
        f"Land proof around {intent.proof_line} and the outcome {intent.primary_outcome}.",
        f"End with CTA text: '{intent.cta_line}'.",
        (
            "Use real people, believable environments, natural motion, social-ad pacing, "
            "captions, continuity between anchor shots, and conversion-focused framing. "
            "Avoid factories, industrial machines, engineering diagrams, gears, robotics, "
            "or abstract mechanical visuals unless the offer genuinely requires them."
        ),
    ]
    return _clip(" ".join(part for part in parts if part), 2500)


def build_kling_request(intent: ProviderNeutralRenderIntent) -> dict[str, str | int]:
    prompt = build_kling_prompt(intent)
    # Kling currently supports 5s and 10s requests. Ad Factory keeps the user-facing
    # intent at 15s/30s while the adapter maps to the closest supported duration.
    provider_duration = 10 if intent.duration_seconds >= 15 else 5
    return {
        "prompt": prompt,
        "duration": provider_duration,
        "aspect_ratio": intent.aspect_ratio,
    }


def build_legacy_kling_prompt(intent: ProviderNeutralRenderIntent) -> dict[str, str | int]:
    return {
        "prompt": build_kling_prompt(intent),
        "duration_seconds": intent.duration_seconds,
    }
