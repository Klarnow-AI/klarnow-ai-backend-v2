import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar

import openai
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.shared.services.openai_compatible import (
    create_async_openai_client,
    get_default_model,
    get_openai_compatible_provider,
    resolve_model_name,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
)


def _log_usage(model: str, usage: Any) -> None:
    """Log token usage for cost tracking."""
    if usage:
        logger.info(
            "[LLM] model=%s prompt_tokens=%d completion_tokens=%d total_tokens=%d",
            model,
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
        )


class OpenAILLM:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        provider = get_openai_compatible_provider()
        self.api_key = api_key or (provider.api_key if provider else "")
        self.default_model = default_model or get_default_model()
        self.client = (
            openai.AsyncOpenAI(api_key=self.api_key, base_url=get_settings().openrouter_base_url)
            if api_key
            else create_async_openai_client()
        )

    @staticmethod
    def _strip_markdown_fences(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.startswith("json"):
            text = text[4:].lstrip()
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        return text

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def parse(
        self,
        system: str,
        user: str,
        schema: Type[T],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
    ) -> T:
        if not self.client:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        model = resolve_model_name(model or self.default_model)
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=True)

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system}\n"
                        "Return only valid JSON that matches the required schema."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{user}\n\n"
                        "JSON schema:\n"
                        f"{schema_json}"
                    ),
                },
            ],
            temperature=temperature,
        )

        _log_usage(model, response.usage)

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise Exception("Failed to parse structured output from LLM")

        data = json.loads(self._strip_markdown_fences(content))
        return schema.model_validate(data)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.client:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        model = resolve_model_name(model or self.default_model)

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,  # pyright: ignore[reportArgumentType]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        _log_usage(model, response.usage)

        return response.choices[0].message.content or ""


def get_llm(
    *,
    api_key: Optional[str] = None,
    default_model: Optional[str] = None,
) -> OpenAILLM:

    return OpenAILLM(api_key=api_key, default_model=default_model)
