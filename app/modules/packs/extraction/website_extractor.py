"""LLM-based brand profile extraction service."""

from typing import Any, Dict, Optional
from app.modules.packs.extraction.schemas import RawBrandProfile
from app.shared.services.llm import OpenAILLM


class WebsiteExtractorService:
    """
    Service to extract brand profiles from website content using LLM with structured output.
    """

    def __init__(
        self,
        llm: OpenAILLM,
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_text_chars: int = 12000,
    ):
        """
        Initialize the website extractor service.

        Args:
            llm: OpenAI LLM instance
            model: Model to use (defaults to LLM's default)
            temperature: Temperature for generation
            max_text_chars: Maximum characters of text to send to LLM
        """
        self.llm = llm
        self.model = model
        self.temperature = temperature
        self.max_text_chars = max_text_chars

    def __call__(self, clean_text: str, meta: Dict[str, Any]) -> RawBrandProfile:
        """Sync call is not supported - use await extract() instead."""
        raise RuntimeError("Call `await extract(...)` instead of __call__ for async usage.")

    def _build_system(self) -> str:
        """Build the system prompt for brand extraction."""
        return (
            "You are a brand intelligence extraction system.\n"
            "Extract a brand profile from website content.\n"
            "Rules:\n"
            "- Do not invent facts.\n"
            "- If a field is not supported by evidence, set it to null (or empty list where appropriate).\n"
            "- Return data strictly matching the provided schema.\n"
        )

    def _build_user(self, clean_text: str, meta: Dict[str, Any]) -> str:
        """
        Build the user prompt with website signals and content.

        Args:
            clean_text: Cleaned website text
            meta: Metadata dictionary with title, description, links, etc.

        Returns:
            Formatted user prompt
        """
        return (
            "Website signals:\n"
            f"Title: {meta.get('title')}\n"
            f"Meta description: {meta.get('meta_description')}\n"
            f"Logo candidates: og_image={meta.get('og_image')} icon={meta.get('icon')}\n"
            f"Known social links: {meta.get('social_links')}\n"
            f"Found emails: {meta.get('emails')}\n"
            f"Found phones: {meta.get('phones')}\n\n"
            "Website text:\n"
            f"{clean_text[: self.max_text_chars]}"
        )

    async def extract(self, clean_text: str, meta: Dict[str, Any]) -> RawBrandProfile:
        """
        Extract brand profile from clean text and metadata.

        Args:
            clean_text: Cleaned website text
            meta: Metadata dictionary

        Returns:
            Extracted brand profile
        """
        system = self._build_system()
        user = self._build_user(clean_text, meta)
        parsed = await self.llm.parse(
            system=system,
            user=user,
            schema=RawBrandProfile,
            model=self.model,
            temperature=self.temperature,
        )
        return parsed


def get_brand_extractor_service(
    llm: OpenAILLM,
    *,
    model: Optional[str] = "gpt-4o-mini",
    temperature: float = 0.0,
) -> WebsiteExtractorService:
    """
    Factory function to create a website extractor service.

    Args:
        llm: OpenAI LLM instance
        model: Model to use (defaults to gpt-4o-mini for this factual extraction task)
        temperature: Temperature for generation (0.0 for fully deterministic extraction)

    Returns:
        WebsiteExtractorService instance
    """
    return WebsiteExtractorService(llm=llm, model=model, temperature=temperature)
