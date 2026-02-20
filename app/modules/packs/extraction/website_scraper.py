"""Website scraping and metadata extraction."""

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
PHONE_RE = re.compile(r"(\+\d{1,3}\s?)?(\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}")
COLOR_RE = re.compile(r"(#(?:[0-9a-fA-F]{3}){1,2}|rgba?\([^)]+\))")

# Limits
MAX_CSS_FILES = 8
MAX_COLORS = 30

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

    # Open Graph image
    og_image = None
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        og_image = urljoin(url, str(og["content"]).strip())

    # Favicon
    icon = None
    icon_tag = soup.find("link", rel=lambda v: bool(v) and "icon" in str(v).lower())
    if icon_tag and icon_tag.get("href"):
        icon = urljoin(url, str(icon_tag["href"]).strip())

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

    # Extract phones
    phones = PHONE_RE.findall(html)
    phone_strings = []
    for phone_match in phones:
        # phone_match is a tuple of groups from the regex
        # Join all non-empty parts to form the complete phone number
        if isinstance(phone_match, tuple):
            # Filter out empty strings and join with no separator
            parts = [p.strip() for p in phone_match if p]
            joined = " ".join(parts) if parts else ""
        else:
            joined = str(phone_match).strip()
        
        if joined and len(joined) >= 7:  # Basic validation: at least 7 chars for a phone
            phone_strings.append(joined)
    
    phone_strings = list(dict.fromkeys(phone_strings))  # Deduplicate while preserving order

    return {
        "title": title,
        "meta_description": meta_desc,
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


async def extract_color_candidates(
    url: str,
    html: str,
    *,
    timeout: float = 8.0,
    client: Optional[httpx.AsyncClient] = None,
) -> List[str]:
    """
    Extract color candidates from HTML inline styles and CSS files.

    Args:
        url: Base URL of the page
        html: HTML content
        timeout: Timeout for CSS file fetching
        client: Optional httpx client to reuse

    Returns:
        List of hex color codes
    """
    soup = BeautifulSoup(html, "lxml")
    colors = set()

    # Extract colors from inline styles
    for tag in soup.find_all(style=True):
        style = tag.get("style")
        if isinstance(style, list):
            style = " ".join(style)
        matches = COLOR_RE.findall(style) if isinstance(style, str) else []
        for m in matches:
            colors.add(m.lower())

    # Collect stylesheet links
    css_links: List[str] = []
    for link in soup.find_all("link", rel="stylesheet"):
        href = as_str_or_none(link.get("href"))
        if href:
            css_links.append(urljoin(url, href))

    # Fetch CSS files async
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

                matches = COLOR_RE.findall(resp.text)
                for m in matches:
                    colors.add(m.lower())
            except httpx.HTTPError:
                continue
    finally:
        if owns_client:
            await client.aclose()

    # Filter out pure white/black
    filtered = [
        c for c in colors if c not in ("#fff", "#ffffff", "#000", "#000000")
    ]

    return filtered[:MAX_COLORS]


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

    # Fill in logo URL if missing
    if not profile.get("logo_url"):
        profile["logo_url"] = meta.get("og_image") or meta.get("icon")

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
    retry=retry_if_exception_type(Exception),
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
