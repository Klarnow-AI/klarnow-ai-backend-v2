"""Streaming helpers for OpenRouter-backed text generation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.shared.services.openai_compatible import (
    create_async_openai_client,
    get_default_model,
)


async def _openai_text_stream(
    *,
    client: AsyncOpenAI,
    system_prompt: str,
    messages: list[dict[str, Any]],
    model: str,
    max_tokens: int | None = None,
) -> AsyncIterator[str]:
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


async def create_text_stream(
    *,
    system_prompt: str,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 8192,
    prelude: str | None = None,
) -> AsyncIterator[str]:
    client = create_async_openai_client()
    if not client:
        raise RuntimeError("Generation is not configured. Set OPENROUTER_API_KEY.")

    return await _prime_text_stream(
        _openai_text_stream(
            client=client,
            system_prompt=system_prompt,
            messages=messages,
            model=model or get_default_model(),
            max_tokens=max_tokens,
        ),
        prelude=prelude,
    )
