import json
import logging
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

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


def _extract_usage(usage: Any) -> dict[str, int]:
    """Normalise the OpenAI/OpenRouter usage object into a plain dict."""
    if not usage:
        return {}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _log_usage(model: str, usage: dict[str, int]) -> None:
    """Log token usage for cost tracking."""
    if usage:
        logger.info(
            "[LLM] model=%s prompt_tokens=%d completion_tokens=%d total_tokens=%d",
            model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
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

    @staticmethod
    def _unwrap_envelope(data: Any, schema: Type[BaseModel]) -> Any:
        """Unwrap accidental schema/envelope wrappers around a structured payload.

        Weaker models sometimes mirror the JSON-Schema shape and return something
        like ``{"properties": {...actual fields...}}`` or ``{"data": {...}}``
        instead of the flat object. If the top-level payload is missing all of
        the target schema's required fields but contains a single nested object
        that *does* have them, use that inner object instead. This is purely a
        last-ditch safety net — the prompt still asks for a flat object.
        """
        if not isinstance(data, dict):
            return data

        json_schema = schema.model_json_schema()
        schema_fields = set((json_schema.get("properties") or {}).keys())
        if not schema_fields:
            return data

        required_fields = set(json_schema.get("required") or [])
        overlap = schema_fields & set(data.keys())
        if overlap and (not required_fields or required_fields & overlap):
            return data

        candidate_keys = ("properties", "data", "result", "schema", "payload", "output")
        for key in candidate_keys:
            inner = data.get(key)
            if isinstance(inner, dict) and schema_fields & set(inner.keys()):
                logger.warning(
                    "[LLM] unwrapping envelope key '%s' for %s — model nested the payload.",
                    key,
                    schema.__name__,
                )
                return inner
        return data

    @staticmethod
    def _describe_schema_fields(schema: Type[BaseModel]) -> str:
        """Render a flat bullet list of fields from a Pydantic model.

        We deliberately *do not* pass the full ``model_json_schema()`` into the
        prompt, because weaker models (notably gpt-4o-mini) tend to mimic the
        envelope — wrapping values under a ``"properties"`` key — instead of
        emitting a plain object. A compact field list keeps the model focused
        on the data shape.
        """
        json_schema = schema.model_json_schema()
        properties = json_schema.get("properties", {}) or {}
        required = set(json_schema.get("required", []) or [])
        lines: list[str] = []
        for name, spec in properties.items():
            type_hint = spec.get("type")
            if not type_hint and "anyOf" in spec:
                variants = [v.get("type") for v in spec["anyOf"] if v.get("type")]
                type_hint = "|".join(v for v in variants if v) or "any"
            if type_hint == "array":
                item_type = (spec.get("items") or {}).get("type") or "any"
                type_hint = f"{item_type}[]"
            flag = "required" if name in required else "optional"
            description = (spec.get("description") or "").strip()
            line = f"- {name} ({type_hint}, {flag})"
            if description:
                line += f": {description}"
            lines.append(line)
        return "\n".join(lines)

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
    ) -> Tuple[T, dict[str, int]]:
        """Call the LLM and parse a structured JSON response.

        Returns a ``(parsed_model, token_usage)`` tuple so callers can persist
        the usage for cost tracking.
        """
        if not self.client:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        model = resolve_model_name(model or self.default_model)
        fields_doc = self._describe_schema_fields(schema)

        system_message = (
            f"{system}\n\n"
            "Output format requirements:\n"
            "- Respond with a single JSON object and nothing else (no prose, no code fences).\n"
            "- The object must contain ONLY the fields listed below, as top-level keys.\n"
            "- Do NOT wrap the object in keys like 'properties', 'schema', 'data', or 'result'.\n"
            "- Do NOT include the field descriptions in the output; emit values only.\n"
            "- Use null for optional fields you cannot fill, and [] for empty lists.\n\n"
            f"Fields (top-level keys of the JSON object):\n{fields_doc}"
        )

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        usage = _extract_usage(response.usage)
        _log_usage(model, usage)

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise Exception("Failed to parse structured output from LLM")

        cleaned = self._strip_markdown_fences(content)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[LLM] model=%s returned non-JSON content (first 500 chars): %s",
                model,
                cleaned[:500],
            )
            raise Exception(f"LLM returned non-JSON content: {exc}") from exc

        data = self._unwrap_envelope(data, schema)
        try:
            return schema.model_validate(data), usage
        except Exception:
            logger.warning(
                "[LLM] model=%s returned JSON that failed %s validation. Payload: %s",
                model,
                schema.__name__,
                json.dumps(data)[:1000],
            )
            raise

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
    ) -> Tuple[str, dict[str, int]]:
        """Call the LLM with an arbitrary message list and return ``(text, usage)``."""
        if not self.client:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        model = resolve_model_name(model or self.default_model)

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,  # pyright: ignore[reportArgumentType]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = _extract_usage(response.usage)
        _log_usage(model, usage)

        return response.choices[0].message.content or "", usage


def get_llm(
    *,
    api_key: Optional[str] = None,
    default_model: Optional[str] = None,
) -> OpenAILLM:

    return OpenAILLM(api_key=api_key, default_model=default_model)
