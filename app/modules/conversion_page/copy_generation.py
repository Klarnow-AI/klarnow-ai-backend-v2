"""Marketing copy generation for conversion pages using GPT-4o."""

import json
from typing import TypedDict

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("klarnow.conversion_page.copy_generation")


class PackContext(TypedDict, total=False):
    """Context data from Pack model for copy generation."""
    brand_name: str
    offer_one_liner: str
    target_audience: str
    primary_cta: str
    usp_locked_line: str
    usp_statement: str
    usp_proof: str
    primary_pain: str
    primary_outcome: str
    hero_angle: str  # speed | quality | specialist | value
    business_type: str  # product | service | coach
    location_city: str | None
    location_country: str | None
    # Brand OS context
    mission: str | None
    voice_str: str | None


class MarketingCopy(TypedDict):
    """Generated marketing copy structure."""
    hero: dict  # headline, subheadline
    benefits: dict  # title, items (list of benefit strings or objects)
    social_proof: dict  # title, quotes (list of testimonial strings)
    lead_form: dict  # headline, subheadline
    cta: dict  # headline, subheadline
    seo: dict  # title, description


def _build_copy_prompt(context: PackContext) -> str:
    """Build comprehensive prompt for marketing copy generation."""
    brand_name = context.get("brand_name", "this brand")
    offer = context.get("offer_one_liner", "our services")
    target_audience = context.get("target_audience", "customers")
    usp_locked = context.get("usp_locked_line", "")
    primary_pain = context.get("primary_pain", "")
    primary_outcome = context.get("primary_outcome", "")
    hero_angle = context.get("hero_angle", "quality")
    business_type = context.get("business_type", "service")
    mission = context.get("mission", "")
    voice = context.get("voice_str", "")
    location = ""
    if context.get("location_city") and context.get("location_country"):
        location = f"Located in {context['location_city']}, {context['location_country']}."

    # Angle-specific emphasis and negative constraints
    angle_instructions = {
        "speed": {
            "do": "Lead with time savings. Use urgency words: 'in minutes', 'instantly', 'same day'. Make the speed feel real and specific.",
            "avoid": "Don't mention quality trade-offs. Avoid passive voice. No 'eventually', 'over time', or vague timelines.",
        },
        "quality": {
            "do": "Lead with craftsmanship and expertise. Use proof-backed language: 'certified', 'award-winning', 'trusted by X'. Convey premium positioning.",
            "avoid": "Don't use hype words ('amazing', 'revolutionary', 'game-changing'). No unverifiable superlatives. Avoid casual tone.",
        },
        "specialist": {
            "do": "Lead with deep expertise in a specific niche. Use authority signals: years of experience, industries served, specific methodologies.",
            "avoid": "Don't be generic about the specialty. No broad claims. Avoid positioning as a generalist.",
        },
        "value": {
            "do": "Lead with ROI and practical outcomes. Make the cost-benefit obvious. Use comparison framing ('fraction of the cost', 'without the overhead').",
            "avoid": "Don't cheapen the brand with discount language. Avoid 'cheap', 'budget', 'affordable' — use 'smart investment' or 'efficient' instead.",
        },
    }
    angle_entry = angle_instructions.get(hero_angle, angle_instructions["quality"])
    angle_guide = f"DO: {angle_entry['do']}\nAVOID: {angle_entry['avoid']}"

    prompt = f"""You are a conversion copywriter creating compelling marketing copy for a landing page.

BRAND CONTEXT:
- Brand Name: {brand_name}
- Offer: {offer}
- Target Audience: {target_audience}
- Business Type: {business_type}
{f'- USP: {usp_locked}' if usp_locked else ''}
{f'- Primary Pain Point: {primary_pain}' if primary_pain else ''}
{f'- Primary Outcome: {primary_outcome}' if primary_outcome else ''}
{f'- Mission: {mission}' if mission else ''}
{f'- Brand Voice: {voice}' if voice else ''}
{f'- {location}' if location else ''}

HERO ANGLE: {hero_angle}
Strategy: {angle_guide}

Generate conversion-optimized copy for the following sections. Return ONLY valid JSON with this exact structure:

{{
  "hero": {{
    "headline": "Compelling benefit-driven headline (5-10 words)",
    "subheadline": "Supporting statement that clarifies the offer (10-15 words)"
  }},
  "benefits": {{
    "title": "Section title (e.g., 'Why Choose {brand_name}')",
    "items": [
      {{"text": "Specific benefit addressing pain point", "icon": "⚡"}},
      {{"text": "Second concrete benefit with measurable outcome", "icon": "🎯"}},
      {{"text": "Third benefit highlighting {hero_angle}", "icon": "✨"}}
    ]
  }},
  "social_proof": {{
    "title": "Social proof section title",
    "quotes": [
      {{"quote": "Realistic testimonial about specific result", "name": "First name + role"}},
      {{"quote": "Second testimonial highlighting different benefit", "name": "First name + role"}}
    ]
  }},
  "lead_form": {{
    "headline": "Call-to-action headline for lead capture",
    "subheadline": "Supporting text explaining what happens next"
  }},
  "cta": {{
    "headline": "Final urgency-driven headline",
    "subheadline": "Brief supporting statement (optional, can be empty string)"
  }},
  "seo": {{
    "title": "SEO-optimized page title (50-60 characters)",
    "description": "Meta description (150-160 characters)"
  }}
}}

REQUIREMENTS:
- Write in a {voice if voice else 'professional and conversational'} tone
- Address the target audience directly: {target_audience}
- Make testimonials sound authentic (real names, specific results, natural language)
- Use power words and emotional triggers appropriate for {business_type}
- Keep headlines punchy and scannable
- Ensure benefits are specific, not generic
- Make the copy feel human-written, not AI-generated

Return ONLY the JSON object, no markdown formatting, no explanations."""

    return prompt


def generate_marketing_copy(context: PackContext, primary_cta: str) -> MarketingCopy:
    """
    Generate complete marketing copy for conversion page using GPT-4o.
    
    Args:
        context: Pack data and Brand OS context
        primary_cta: Locked CTA label from campaign
        
    Returns:
        MarketingCopy dict with all section content
        
    Raises:
        ValueError: If OpenAI API key not configured or generation fails
    """
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, returning fallback copy")
        return _fallback_copy(context, primary_cta)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = _build_copy_prompt(context)

        logger.info(f"Generating marketing copy for brand: {context.get('brand_name', 'unknown')}")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert direct-response copywriter with 15+ years of experience. "
                        "Your copy drives measurable action: clicks, form fills, purchases.\n\n"
                        "Success criteria for every output:\n"
                        "- Hero headline passes the 5-second test (visitor immediately understands the offer)\n"
                        "- Benefits are outcome-focused (customer result, not feature list)\n"
                        "- CTA is singular and specific — never generic 'Learn More'\n"
                        "- Testimonials sound authentic: real first names, specific results, natural language\n"
                        "- Tone matches the brand voice exactly\n\n"
                        "Return only valid JSON. No markdown fences, no explanations."
                    ),
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.75,
            max_tokens=2000,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        # Clean markdown formatting if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        copy_data = json.loads(content)
        
        # Validate structure
        required_keys = {"hero", "benefits", "social_proof", "lead_form", "cta", "seo"}
        if not all(k in copy_data for k in required_keys):
            logger.error(f"Missing required keys in generated copy: {required_keys - copy_data.keys()}")
            return _fallback_copy(context, primary_cta)

        logger.info("Marketing copy generated successfully")
        return copy_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {e}")
        return _fallback_copy(context, primary_cta)
    except Exception as e:
        logger.error(f"Error generating marketing copy: {e}")
        return _fallback_copy(context, primary_cta)


def _fallback_copy(context: PackContext, primary_cta: str) -> MarketingCopy:
    """
    Generate fallback copy using templates when LLM generation fails.
    Better than placeholders but not as good as LLM-generated content.
    """
    brand_name = context.get("brand_name", "Our Brand")
    offer = context.get("offer_one_liner", "our services")
    target_audience = context.get("target_audience", "businesses like yours")
    usp_statement = context.get("usp_statement", "exceptional service")
    primary_outcome = context.get("primary_outcome", "achieve your goals")
    hero_angle = context.get("hero_angle", "quality")

    # Angle-specific headlines
    headline_templates = {
        "speed": f"{brand_name}: {primary_outcome or 'Results'} Delivered Fast",
        "quality": f"Premium {offer} for {target_audience}",
        "specialist": f"Expert {offer} Built for {target_audience}",
        "value": f"Affordable {offer} That Delivers Results",
    }
    
    headline = headline_templates.get(hero_angle, f"{brand_name}: {offer}")
    
    return {
        "hero": {
            "headline": headline,
            "subheadline": f"Join hundreds of satisfied customers who chose {brand_name} for {usp_statement}"
        },
        "benefits": {
            "title": f"Why Choose {brand_name}",
            "items": [
                {"text": f"Proven track record with {target_audience}", "icon": "⚡"},
                {"text": f"Focused on helping you {primary_outcome or 'succeed'}", "icon": "🎯"},
                {"text": f"Backed by our commitment to {usp_statement}", "icon": "✨"}
            ]
        },
        "social_proof": {
            "title": "What Our Customers Say",
            "quotes": [
                {"quote": f"Working with {brand_name} exceeded our expectations. Highly recommend!", "name": "Sarah M., Business Owner"},
                {"quote": f"The {usp_statement} really made a difference for us.", "name": "James T., Manager"}
            ]
        },
        "lead_form": {
            "headline": "Ready to Get Started?",
            "subheadline": "Fill out the form and we'll be in touch within 24 hours"
        },
        "cta": {
            "headline": "Take the Next Step Today",
            "subheadline": f"Join {target_audience} who are already seeing results"
        },
        "seo": {
            "title": f"{brand_name} | {offer}",
            "description": f"{brand_name} offers {offer} for {target_audience}. {usp_statement}. Contact us to learn more."
        }
    }
