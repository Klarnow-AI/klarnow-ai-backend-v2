"""Streaming helpers for OpenAI and Anthropic text generation."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings


logger = logging.getLogger(__name__)
_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


def _normalize_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        normalized_message = dict(message)
        if normalized_message.get("role") == "system":
            # Anthropic accepts top-level `system`, but not `system` inside `messages`.
            normalized_message["role"] = "assistant"
        normalized.append(normalized_message)
    return normalized


def _sanitize_anthropic_thinking_budget(
    *,
    max_tokens: int,
    thinking_budget: int | None,
) -> int | None:
    if thinking_budget is None:
        return None
    if thinking_budget <= 0:
        logger.warning(
            "Skipping Anthropic thinking budget because it is non-positive: %s",
            thinking_budget,
        )
        return None

    max_budget = max_tokens - 1
    if max_budget <= 0:
        logger.warning(
            "Skipping Anthropic thinking budget because max_tokens=%s leaves no room for output",
            max_tokens,
        )
        return None

    if thinking_budget > max_budget:
        logger.warning(
            "Clamping Anthropic thinking budget from %s to %s to stay below max_tokens=%s",
            thinking_budget,
            max_budget,
            max_tokens,
        )
        return max_budget
    return thinking_budget


def _build_anthropic_payload(
    *,
    system_prompt: str,
    messages: list[dict[str, Any]],
    model: str,
    max_tokens: int,
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": _normalize_anthropic_messages(messages),
        "stream": True,
    }
    sanitized_thinking_budget = _sanitize_anthropic_thinking_budget(
        max_tokens=max_tokens,
        thinking_budget=thinking_budget,
    )
    if sanitized_thinking_budget is not None:
        payload["thinking"] = {
            "type": "enabled",
            "budget_tokens": sanitized_thinking_budget,
        }
    return payload


def _extract_anthropic_http_error_message(body: bytes) -> str | None:
    if not body:
        return None

    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return text


async def _openai_text_stream(
    *,
    api_key: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    model: str,
    max_tokens: int | None = None,
) -> AsyncIterator[str]:
    client = AsyncOpenAI(api_key=api_key)
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if isinstance(delta, str) and delta:
                yield delta
                continue
            if isinstance(delta, list):
                for part in delta:
                    text = None
                    if isinstance(part, dict):
                        text = part.get("text")
                    else:
                        text = getattr(part, "text", None)
                    if isinstance(text, str) and text:
                        yield text
    finally:
        await client.close()


def _parse_sse_event(raw_event: str) -> tuple[str | None, str]:
    event_name = None
    data_lines: list[str] = []
    for line in raw_event.splitlines():
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
    return event_name, "\n".join(data_lines)


async def _anthropic_text_stream(
    *,
    api_key: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    model: str,
    max_tokens: int,
    thinking_budget: int | None = None,
) -> AsyncIterator[str]:
    payload = _build_anthropic_payload(
        system_prompt=system_prompt,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        thinking_budget=thinking_budget,
    )

    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    timeout = httpx.Timeout(60.0, connect=20.0, read=120.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", _ANTHROPIC_API_URL, headers=headers, json=payload) as response:
            if response.is_error:
                body = await response.aread()
                detail = _extract_anthropic_http_error_message(body)
                message = f"Anthropic request failed with status {response.status_code}"
                if detail:
                    message += f": {detail}"
                raise RuntimeError(message)
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    raw_event, buffer = buffer.split("\n\n", 1)
                    event_name, data = _parse_sse_event(raw_event)
                    text = _extract_anthropic_text(event_name, data)
                    if text:
                        yield text
            if buffer.strip():
                event_name, data = _parse_sse_event(buffer)
                text = _extract_anthropic_text(event_name, data)
                if text:
                    yield text


def _extract_anthropic_text(event_name: str | None, data: str) -> str | None:
    if not data or data == "[DONE]":
        return None

    payload = json.loads(data)
    payload_type = payload.get("type")
    normalized_event = event_name or payload_type

    if normalized_event == "error" or payload_type == "error":
        error = payload.get("error") or {}
        message = error.get("message") or "Anthropic stream failed"
        raise RuntimeError(str(message))

    if normalized_event != "content_block_delta" and payload_type != "content_block_delta":
        return None

    delta = payload.get("delta") or {}
    if delta.get("type") != "text_delta":
        return None

    text = delta.get("text")
    return text if isinstance(text, str) and text else None


async def _prime_text_stream(
    stream: AsyncIterator[str],
    *,
    prelude: str | None = None,
) -> AsyncIterator[str]:
    iterator = stream.__aiter__()

    while True:
        try:
            first_chunk = await iterator.__anext__()
        except StopAsyncIteration as exc:
            raise RuntimeError("Model returned no content") from exc
        if first_chunk:
            break

    async def wrapped() -> AsyncIterator[str]:
        if prelude:
            yield prelude
        yield first_chunk
        async for chunk in iterator:
            if chunk:
                yield chunk

    return wrapped()


async def create_text_stream_with_fallback(
    *,
    system_prompt: str,
    openai_messages: list[dict[str, Any]],
    anthropic_messages: list[dict[str, Any]] | None = None,
    openai_model: str = "gpt-4o",
    anthropic_model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    anthropic_thinking_budget: int | None = None,
    prelude: str | None = None,
) -> AsyncIterator[str]:
    settings = get_settings()
    openai_key = settings.openai_api_key.strip()
    anthropic_key = settings.anthropic_api_key.strip()

    if not anthropic_key and not openai_key:
        raise RuntimeError(
            "Generation is not configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
        )

    last_error: Exception | None = None

    if anthropic_key:
        try:
            return await _prime_text_stream(
                _anthropic_text_stream(
                    api_key=anthropic_key,
                    system_prompt=system_prompt,
                    messages=anthropic_messages or openai_messages,
                    model=anthropic_model,
                    max_tokens=max_tokens,
                    thinking_budget=anthropic_thinking_budget,
                ),
                prelude=prelude,
            )
        except Exception as exc:
            last_error = exc
            logger.exception("Anthropic generation failed")
            if not openai_key:
                raise

    if openai_key:
        try:
            return await _prime_text_stream(
                _openai_text_stream(
                    api_key=openai_key,
                    system_prompt=system_prompt,
                    messages=openai_messages,
                    model=openai_model,
                    max_tokens=max_tokens,
                ),
                prelude=prelude,
            )
        except Exception as exc:
            last_error = exc
            logger.exception("OpenAI generation failed")
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("No generation provider is available")
