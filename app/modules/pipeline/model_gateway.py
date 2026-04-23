"""Model gateway — wraps LLM calls with tier routing, retries, and token tracking."""

from __future__ import annotations

import logging
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from app.shared.services.llm import OpenAILLM
from .config import MODEL_TIERS

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_llm: OpenAILLM | None = None


def _get_llm() -> OpenAILLM:
    global _llm
    if _llm is None:
        _llm = OpenAILLM()
    return _llm


async def generate_structured(
    *,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    model_tier: str = "default",
    temperature: float = 0.1,
) -> tuple[T, dict[str, Any]]:
    """Call the LLM and parse the response into a Pydantic model.

    Returns ``(parsed_model, metadata_dict)`` where ``metadata`` carries
    ``model_id``, ``latency_ms`` and ``token_usage`` so the orchestrator can
    persist them on the ``StageRun`` for cost/latency tracking.
    """
    model_id = MODEL_TIERS.get(model_tier, MODEL_TIERS["default"])
    llm = _get_llm()

    start = time.perf_counter()
    result, usage = await llm.parse(
        system=system_prompt,
        user=user_prompt,
        schema=response_model,
        model=model_id,
        temperature=temperature,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "[ModelGateway] tier=%s model=%s schema=%s latency_ms=%d total_tokens=%d",
        model_tier,
        model_id,
        response_model.__name__,
        latency_ms,
        usage.get("total_tokens", 0),
    )

    metadata = {
        "model_id": model_id,
        "latency_ms": latency_ms,
        "token_usage": usage,
    }
    return result, metadata


async def generate_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model_tier: str = "default",
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Call the LLM and return a raw text response.

    Returns ``(text, metadata_dict)``.
    """
    model_id = MODEL_TIERS.get(model_tier, MODEL_TIERS["default"])
    llm = _get_llm()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    start = time.perf_counter()
    text, usage = await llm.chat(
        messages=messages,
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "[ModelGateway] tier=%s model=%s text_len=%d latency_ms=%d total_tokens=%d",
        model_tier,
        model_id,
        len(text),
        latency_ms,
        usage.get("total_tokens", 0),
    )

    metadata = {
        "model_id": model_id,
        "latency_ms": latency_ms,
        "token_usage": usage,
    }
    return text, metadata
