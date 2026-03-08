"""Website scraping and metadata extraction."""

import colorsys
import re
from typing import Any, Dict, List, Optional, Tuple, cast
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.modules.packs.extraction.schemas import WebsiteExtractedIngestion
from app.modules.packs.extraction.website_extractor import get_brand_extractor_service
from app.shared.functions.string import as_str_or_none
from app.shared.services.llm import OpenAILLM


# Social media domains to detect
SOCIAL_DOMAINS = (
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "github.com",
)

# Regex patterns for contact info and colors
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Matches international phone numbers only (must start with +country code).
# Groups of digits separated by spaces, hyphens, dots or parens — e.g.:
#   +44 161 696 0976   or   +441616960976
PHONE_RE = re.compile(
    r"\+\d{1,3}"                        # + and country code (1–3 digits)
    r"(?:[\s\-.]?\(?\d{1,5}\)?){2,5}"  # 2–5 groups of digits, optional separators
    r"(?!\d)"                            # must not run into more digits
)
COLOR_RE = re.compile(r"(#(?:[0-9a-fA-F]{3}){1,2}|rgba?\([^)]+\))")

# Limits
MAX_CSS_FILES = 8
MAX_BRAND_COLORS = 3  # Return the top 3 high-confidence brand colors

# Keywords that identify CTA elements in CSS selectors and HTML classes
_CTA_KEYWORDS = frozenset(["btn", "button", "cta", "action", "primary", "submit", "hero"])

# Parses CSS rule blocks: captures (selector, properties)
_CSS_RULE_RE = re.compile(r"([^{};@][^{}]*)\{([^{}]+)\}", re.DOTALL)

# Default headers for requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BrandExtractor/1.0; +https://example.com/bot)"
}


async def fetch_html(
    url: str,
    *,
    timeout: float = 20.0,
    client: Optional[httpx.AsyncClient] = None,
) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        client: Optional httpx client to reuse

    Returns:
        HTML content as string

    Raises:
        httpx.HTTPError: If request fails
    """
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True
        )

    try:
        r = await client.get(url)
        r.raise_for_status()
        return r.text
    finally:
        if owns_client:
            await client.aclose()


def html_to_clean_text(url: str, html: str) -> str:
    """
    Extract clean text from HTML using readability and BeautifulSoup.

    Args:
        url: URL of the page (for context)
        html: HTML content

    Returns:
        Clean text content
    """
    # Use readability to extract main content
    doc = Document(html)
    content_html = doc.summary(html_partial=True)

    # Parse with BeautifulSoup and remove scripts/styles
    soup = BeautifulSoup(content_html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Extract text
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def extract_meta_and_links(url: str, html: str) -> Dict[str, Any]:
    """
    Extract metadata and links from HTML.

    Args:
        url: Base URL of the page
        html: HTML content

    Returns:
        Dictionary with title, meta_description, og_image, icon, social_links, emails, phones
    """
    soup = BeautifulSoup(html, "lxml")

    # Title
    title = soup.title.text.strip() if soup.title and soup.title.text else None

    # Meta description
    meta_desc = None
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = str(md["content"]).strip()

    # Open Graph image (kept for fallback use)
    og_image = None
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        og_image = urljoin(url, str(og["content"]).strip())

    # Favicon
    icon = None
    icon_tag = soup.find("link", rel=lambda v: bool(v) and "icon" in str(v).lower())
    if icon_tag and icon_tag.get("href"):
        icon = urljoin(url, str(icon_tag["href"]).strip())

    # Logo detection — priority chain:
    #   1. <img> with "logo" in class / id / alt / src  (most reliable)
    #   2. <link rel="apple-touch-icon">                (higher-res brand icon)
    #   3. og:image                                      (social sharing image, not always a logo)
    #   4. favicon                                       (last resort)
    logo_url: Optional[str] = None
    for img in soup.find_all("img"):
        src = as_str_or_none(img.get("src"))
        if not src:
            continue
        alt = (img.get("alt") or "").lower()
        cls = " ".join(img.get("class") or []).lower()
        img_id = (img.get("id") or "").lower()
        if any("logo" in x for x in [alt, cls, img_id, src.lower()]):
            logo_url = urljoin(url, src)
            break

    if not logo_url:
        apple = soup.find(
            "link",
            rel=lambda v: bool(v) and "apple-touch-icon" in " ".join(v if isinstance(v, list) else [str(v)]).lower(),
        )
        if apple and apple.get("href"):
            logo_url = urljoin(url, str(apple["href"]).strip())

    if not logo_url:
        logo_url = og_image or icon

    # Extract all links
    anchors = [a.get("href") for a in soup.find_all("a", href=True)]
    abs_links = [urljoin(url, cast(str, h)) for h in anchors if h]

    # Filter social links
    social_links = []
    for link in abs_links:
        if any(d in link for d in SOCIAL_DOMAINS):
            social_links.append(link)
    social_links = sorted(set(social_links))

    # Extract emails
    emails = sorted(set(EMAIL_RE.findall(html)))

    # Extract international phone numbers.
    # Validate digit count against E.164 bounds (country code + subscriber = 8–15 digits).
    phone_strings = []
    for m in PHONE_RE.finditer(html):
        phone = m.group(0).strip()
        digit_count = sum(c.isdigit() for c in phone)
        if 8 <= digit_count <= 15:
            phone_strings.append(phone)
    phone_strings = list(dict.fromkeys(phone_strings))  # Deduplicate while preserving order

    return {
        "title": title,
        "meta_description": meta_desc,
        "logo_url": logo_url,
        "og_image": og_image,
        "icon": icon,
        "social_links": social_links,
        "emails": emails,
        "phones": phone_strings,
    }


def pick_candidate_pages(base_url: str, html: str, max_pages: int = 3) -> List[str]:
    """
    Pick candidate pages to crawl for additional context (e.g., /about, /contact).

    Args:
        base_url: Base URL of the website
        html: HTML content of the main page
        max_pages: Maximum number of candidate pages to return

    Returns:
        List of URLs to crawl
    """
    soup = BeautifulSoup(html, "lxml")
    candidates = []

    for a in soup.find_all("a", href=True):
        href = str(a["href"] or "").strip()
        text = (a.get_text() or "").strip().lower()
        full = urljoin(base_url, href)

        # Look for about/company pages
        if any(k in full.lower() for k in ["/about", "/company", "/who-we-are"]):
            candidates.append(full)
        # Look for contact/support pages
        if any(k in full.lower() for k in ["/contact", "/support"]):
            candidates.append(full)
        # Check link text
        if "about" in text or "contact" in text:
            candidates.append(full)

    # Filter to same domain and deduplicate
    unique = []
    for u in candidates:
        if u.startswith(base_url) and u not in unique:
            unique.append(u)

    return unique[:max_pages]


def _is_css_noise_color(hex_color: str) -> bool:
    """
    Return True if this hex color is likely a background, text, border, or utility color
    rather than a brand color. Filters near-whites, near-blacks, and low-saturation grays.
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) != 6:
        return True
    try:
        r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    except ValueError:
        return True
    _, saturation, value = colorsys.rgb_to_hsv(r, g, b)
    # Near-white: high brightness, low saturation
    if value > 0.92 and saturation < 0.12:
        return True
    # Near-black: very low brightness
    if value < 0.12:
        return True
    # Gray: low saturation across all brightnesses
    if saturation < 0.15:
        return True
    return False


def _score_colors_from_html(soup: BeautifulSoup) -> Dict[str, float]:
    """
    Score hex colors found in the HTML by how prominently they appear on CTAs and page elements.

    Scoring:
      - CTA element inline style  → 3.0  (button, input[submit], a.btn, etc.)
      - Any other inline style    → 0.5
    """
    scores: Dict[str, float] = {}

    def _add(color: str, score: float) -> None:
        c = color.lower()
        if c.startswith("#") and not _is_css_noise_color(c):
            scores[c] = scores.get(c, 0) + score

    # Identify CTA elements: all <button>, <input type=submit/button>,
    # and <a>/<div>/<span> whose class contains a CTA keyword.
    cta_tags = set()
    for tag in soup.find_all(["button", "input", "a", "div", "span"]):
        if tag.name in ("button",):
            cta_tags.add(id(tag))
        elif tag.name == "input" and tag.get("type", "").lower() in ("submit", "button"):
            cta_tags.add(id(tag))
        else:
            cls = " ".join(tag.get("class") or []).lower()
            if any(kw in cls for kw in _CTA_KEYWORDS):
                cta_tags.add(id(tag))

    for tag in soup.find_all(style=True):
        style = tag.get("style") or ""
        if isinstance(style, list):
            style = " ".join(style)
        score = 3.0 if id(tag) in cta_tags else 0.5
        for m in COLOR_RE.finditer(style):
            _add(m.group(1), score)

    return scores


def _score_colors_from_css(css_text: str) -> Dict[str, float]:
    """
    Score hex colors found in CSS text. Rules whose selectors contain CTA keywords
    get a higher weight than general rules.

    Scoring:
      - CTA selector rule   → 2.0
      - General rule        → 0.3
    """
    scores: Dict[str, float] = {}
    for rule in _CSS_RULE_RE.finditer(css_text):
        selector = rule.group(1).lower()
        props = rule.group(2)
        is_cta = any(kw in selector for kw in _CTA_KEYWORDS)
        score = 2.0 if is_cta else 0.3
        for m in COLOR_RE.finditer(props):
            color = m.group(1).lower()
            if color.startswith("#") and not _is_css_noise_color(color):
                scores[color] = scores.get(color, 0) + score
    return scores


async def extract_color_candidates(
    url: str,
    html: str,
    *,
    timeout: float = 8.0,
    client: Optional[httpx.AsyncClient] = None,
) -> List[str]:
    """
    Extract the top 3 brand color candidates by scoring hex colors found in
    CTA elements, inline styles, and CSS files.

    CTA inline styles score highest (3.0), followed by CSS CTA rules (2.0),
    general inline styles (0.5), and general CSS rules (0.3).
    Grays, near-whites, and near-blacks are filtered out.

    Returns:
        Up to 3 hex color strings ordered by confidence score.
    """
    soup = BeautifulSoup(html, "lxml")

    # Score colors from HTML inline styles, weighting CTAs heavily
    scores: Dict[str, float] = _score_colors_from_html(soup)

    # Collect and fetch stylesheet links
    css_links: List[str] = []
    for link in soup.find_all("link", rel="stylesheet"):
        href = as_str_or_none(link.get("href"))
        if href:
            css_links.append(urljoin(url, href))

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True
        )

    try:
        for css_url in css_links[:MAX_CSS_FILES]:
            try:
                resp = await client.get(css_url)
                if resp.status_code >= 400:
                    continue
                for color, score in _score_colors_from_css(resp.text).items():
                    scores[color] = scores.get(color, 0) + score
            except httpx.HTTPError:
                continue
    finally:
        if owns_client:
            await client.aclose()

    # Return the top MAX_BRAND_COLORS colors ranked by accumulated score
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [color for color, _ in ranked[:MAX_BRAND_COLORS]]


def merge_deterministic(profile: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge LLM-extracted profile with deterministic metadata.

    Args:
        profile: LLM-extracted brand profile
        meta: Metadata from HTML extraction

    Returns:
        Merged profile dictionary
    """
    # Ensure contact_info exists and is a dict
    if "contact_info" not in profile or profile["contact_info"] is None:
        profile["contact_info"] = {}
    
    # Convert ContactInfo model to dict if needed
    if hasattr(profile["contact_info"], "model_dump"):
        profile["contact_info"] = profile["contact_info"].model_dump()

    # Fill in contact info if missing
    if not profile["contact_info"].get("email") and meta.get("emails"):
        profile["contact_info"]["email"] = meta["emails"][0]
    if not profile["contact_info"].get("phone") and meta.get("phones"):
        profile["contact_info"]["phone"] = meta["phones"][0]

    # Fill in social links if missing
    if not profile.get("social_links") and meta.get("social_links"):
        profile["social_links"] = meta["social_links"]

    # Fill in logo URL if missing — prefer the curated logo_url from meta detection
    if not profile.get("logo_url"):
        profile["logo_url"] = meta.get("logo_url") or meta.get("og_image") or meta.get("icon")

    return profile


def validate_profile(profile: Dict[str, Any]) -> WebsiteExtractedIngestion:
    """
    Validate and convert profile dict to WebsiteExtractedIngestion schema.

    Args:
        profile: Profile dictionary

    Returns:
        Validated WebsiteExtractedIngestion instance
    """
    return WebsiteExtractedIngestion.model_validate(profile)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    # Retry transient fetch errors, but do not replay completed LLM work.
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
async def extract_brand_from_website(
    url: str,
    llm: OpenAILLM,
) -> Tuple[WebsiteExtractedIngestion, List[str]]:
    """
    Main function to extract brand profile and colors from a website.

    Args:
        url: Website URL to extract from
        llm: OpenAI LLM instance

    Returns:
        Tuple of (profile, color_candidates)

    Raises:
        Exception: If extraction fails after retries
    """
    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        # 1) Fetch main page
        html = await fetch_html(url, client=client)

        # 2) Extract colors + meta from main HTML
        color_candidates = await extract_color_candidates(url, html, client=client)
        meta = extract_meta_and_links(url, html)

        # 3) Build clean text corpus (main + candidate pages)
        texts = [html_to_clean_text(url, html)]

        for page in pick_candidate_pages(url, html):
            try:
                page_html = await fetch_html(page, client=client)
                texts.append(html_to_clean_text(page, page_html))
            except Exception:
                continue

    combined = "\n\n".join(texts)

    # 4) Extract brand profile using LLM
    extractor = get_brand_extractor_service(llm=llm)
    raw_profile = await extractor.extract(combined, meta)
    raw = raw_profile.model_dump()

    # 5) Merge with deterministic metadata
    merged = merge_deterministic(raw, meta)
    profile = validate_profile(merged)

    return profile, color_candidates


async def ingest_and_extract_website(url: str, llm: OpenAILLM) -> Dict[str, Any]:
    """
    Convenience function to extract brand profile and colors from a website.

    Args:
        url: Website URL
        llm: OpenAI LLM instance

    Returns:
        Dictionary with 'brand_profile' and 'color_candidates'
    """
    profile, color_candidates = await extract_brand_from_website(url, llm)
    return {
        "brand_profile": profile.model_dump(),
        "color_candidates": color_candidates,
    }
