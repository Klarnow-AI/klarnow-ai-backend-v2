import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

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
        default_model: str = "gpt-4o",
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.default_model = default_model
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

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
            raise RuntimeError("OpenAI API key not configured")

        model = model or self.default_model

        response = await self.client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format=schema,
        )

        _log_usage(model, response.usage)

        parsed = response.choices[0].message.parsed
        if parsed is None:
            content = response.choices[0].message.content
            if content:
                try:
                    data = json.loads(content)
                    return schema.model_validate(data)
                except Exception:
                    pass
            raise Exception("Failed to parse structured output from LLM")

        return parsed

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
            raise RuntimeError("OpenAI API key not configured")

        model = model or self.default_model

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
    default_model: str = "gpt-4o",
) -> OpenAILLM:

    return OpenAILLM(api_key=api_key, default_model=default_model)
