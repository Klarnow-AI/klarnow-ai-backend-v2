"""Design token generation for conversion pages using GPT-4o."""

import json
from typing import TypedDict

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("klarnow.conversion_page.design_generation")


class DesignTokens(TypedDict):
    """CSS-compatible design tokens for conversion page styling."""
    primaryColor: str  # Hex color
    secondaryColor: str  # Hex color
    accentColor: str  # Hex color
    textColor: str  # Hex color
    backgroundColor: str  # Hex color
    fontHeading: str  # Font family name
    fontBody: str  # Font family name
    borderRadius: str  # CSS value (e.g., "12px")
    spacing: str  # Base spacing unit (e.g., "16px")


def _build_design_prompt(
    brand_name: str,
    business_type: str,
    hero_angle: str,
    existing_brand_colors: dict | None = None,
) -> str:
    """Build prompt for design token generation."""
    
    # Business type design guidance
    type_guidance = {
        "product": "Modern e-commerce aesthetic, product-focused, trust-building colors",
        "service": "Professional service industry look, reliable and approachable, balanced colors",
        "coach": "Authority and expertise, inspirational and aspirational, premium feel",
    }
    
    # Hero angle color psychology
    angle_psychology = {
        "speed": "Energetic, dynamic colors (oranges, reds, vibrant blues) that convey urgency and action",
        "quality": "Premium, sophisticated colors (deep blues, purples, elegant grays) that convey luxury",
        "specialist": "Professional, focused colors (teals, navy, deep greens) that convey expertise",
        "value": "Trustworthy, practical colors (greens, blues, warm neutrals) that convey reliability",
    }
    
    type_desc = type_guidance.get(business_type, type_guidance["service"])
    angle_psych = angle_psychology.get(hero_angle, angle_psychology["quality"])
    
    brand_color_context = ""
    if existing_brand_colors:
        colors = ", ".join([f"{k}: {v}" for k, v in existing_brand_colors.items() if v])
        brand_color_context = f"\n\nEXISTING BRAND COLORS (incorporate if provided):\n{colors}"
    
    prompt = f"""You are a conversion-focused UI/UX designer creating a design system for a landing page.

BRAND CONTEXT:
- Brand Name: {brand_name}
- Business Type: {business_type}
- Hero Angle: {hero_angle}

DESIGN REQUIREMENTS:
- Business Type Aesthetic: {type_desc}
- Color Psychology: {angle_psych}
- Must be conversion-optimized (high contrast, clear hierarchy)
- Must be WCAG AA accessible (contrast ratios 4.5:1 minimum)
- Modern, professional, trustworthy appearance
{brand_color_context}

Generate a complete design token system. Return ONLY valid JSON with this exact structure:

{{
  "primaryColor": "#hex_color (main brand color, used for CTAs and key actions)",
  "secondaryColor": "#hex_color (supporting color for accents and secondary elements)",
  "accentColor": "#hex_color (highlight color for important information)",
  "textColor": "#hex_color (primary text color, high contrast against background)",
  "backgroundColor": "#hex_color (page background, usually white or very light)",
  "fontHeading": "Font name (modern, readable, appropriate for {business_type})",
  "fontBody": "Font name (highly readable body font)",
  "borderRadius": "value (e.g., '8px' or '12px' for modern rounded corners)",
  "spacing": "value (base spacing unit, e.g., '16px')"
}}

FONT REQUIREMENTS:
- Use only web-safe or Google Fonts that are free and widely available
- Heading fonts: can be distinctive but must remain professional
- Body fonts: prioritize readability (Inter, Open Sans, Roboto, Lato, etc.)
- Avoid overly decorative or script fonts

COLOR REQUIREMENTS:
- Ensure all colors work well together
- Primary color should be bold enough for CTAs
- Text color must have 4.5:1 contrast ratio with background
- Avoid pure black (#000000) for text; use slightly softer dark grays
- Background should be light (white or very light gray)

Return ONLY the JSON object, no markdown formatting, no explanations."""

    return prompt


def generate_design_tokens(
    brand_name: str,
    business_type: str,
    hero_angle: str,
    existing_brand_colors: dict | None = None,
) -> DesignTokens:
    """
    Generate design tokens for conversion page using GPT-4o.
    
    Args:
        brand_name: Brand name
        business_type: product | service | coach
        hero_angle: speed | quality | specialist | value
        existing_brand_colors: Optional dict of existing brand colors
        
    Returns:
        DesignTokens dict with CSS-compatible values
        
    Raises:
        ValueError: If OpenAI API key not configured or generation fails
    """
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, returning fallback design tokens")
        return _fallback_design_tokens(business_type, hero_angle)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = _build_design_prompt(brand_name, business_type, hero_angle, existing_brand_colors)

        logger.info(f"Generating design tokens for brand: {brand_name}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional UI/UX designer specializing in conversion-optimized landing pages. Return only valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=800,
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

        tokens = json.loads(content)
        
        # Validate required keys
        required_keys = {
            "primaryColor", "secondaryColor", "accentColor", 
            "textColor", "backgroundColor", "fontHeading", 
            "fontBody", "borderRadius", "spacing"
        }
        if not all(k in tokens for k in required_keys):
            logger.error(f"Missing required keys in generated tokens: {required_keys - tokens.keys()}")
            return _fallback_design_tokens(business_type, hero_angle)

        # Validate color format (basic check for hex colors)
        for key in ["primaryColor", "secondaryColor", "accentColor", "textColor", "backgroundColor"]:
            if not tokens[key].startswith("#") or len(tokens[key]) not in [4, 7]:
                logger.error(f"Invalid color format for {key}: {tokens[key]}")
                return _fallback_design_tokens(business_type, hero_angle)

        logger.info("Design tokens generated successfully")
        return tokens

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {e}")
        return _fallback_design_tokens(business_type, hero_angle)
    except Exception as e:
        logger.error(f"Error generating design tokens: {e}")
        return _fallback_design_tokens(business_type, hero_angle)


def _fallback_design_tokens(business_type: str, hero_angle: str) -> DesignTokens:
    """
    Generate fallback design tokens using predefined palettes.
    Professional defaults when LLM generation fails.
    """
    # Angle-specific color palettes
    angle_palettes = {
        "speed": {
            "primaryColor": "#f97316",  # Orange
            "secondaryColor": "#fb923c",  # Light orange
            "accentColor": "#dc2626",  # Red
        },
        "quality": {
            "primaryColor": "#6366f1",  # Indigo
            "secondaryColor": "#8b5cf6",  # Purple
            "accentColor": "#7c3aed",  # Violet
        },
        "specialist": {
            "primaryColor": "#0891b2",  # Cyan
            "secondaryColor": "#06b6d4",  # Light cyan
            "accentColor": "#0e7490",  # Dark cyan
        },
        "value": {
            "primaryColor": "#16a34a",  # Green
            "secondaryColor": "#22c55e",  # Light green
            "accentColor": "#15803d",  # Dark green
        },
    }
    
    # Business type font pairings
    type_fonts = {
        "product": {"heading": "Inter", "body": "Inter"},
        "service": {"heading": "Roboto", "body": "Open Sans"},
        "coach": {"heading": "Playfair Display", "body": "Lato"},
    }
    
    palette = angle_palettes.get(hero_angle, angle_palettes["quality"])
    fonts = type_fonts.get(business_type, type_fonts["service"])
    
    return {
        "primaryColor": palette["primaryColor"],
        "secondaryColor": palette["secondaryColor"],
        "accentColor": palette["accentColor"],
        "textColor": "#1f2937",  # Dark gray (not pure black)
        "backgroundColor": "#ffffff",  # White
        "fontHeading": fonts["heading"],
        "fontBody": fonts["body"],
        "borderRadius": "12px",
        "spacing": "16px",
    }
