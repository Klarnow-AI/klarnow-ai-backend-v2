"""Chat turn: LLM with pack context and tool calling; Use / Preview / Apply."""

from __future__ import annotations

import json
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.storage import get_presigned_url
from app.modules.agents.orchestrator import assemble_context, CHAT_CONTEXT_LAST_N_MESSAGES
from app.modules.agents.registry import REGISTRY, execute
from app.modules.packs.services import get_pack_for_user
from app.shared.services.reference_kb import get_reference_kb

logger = get_logger("klarnow.chat.reference_kb")


ACCOUNT_SCOPE_TOOL_NAMES = {"get_account_snapshot"}

ACCOUNT_SCOPE_PATTERNS = [
    re.compile(r"\bacross\s+all\s+packs\b", re.IGNORECASE),
    re.compile(r"\ball\s+packs\b", re.IGNORECASE),
    re.compile(r"\baccount[-\s]?wide\b", re.IGNORECASE),
    re.compile(r"\bentire\s+account\b", re.IGNORECASE),
    re.compile(r"\bmy\s+account\b", re.IGNORECASE),
]

FOLLOWUP_KEYWORDS = (
    "follow-up",
    "follow up",
    "queue",
    "overdue",
)
LEADS_KEYWORDS = ("lead", "leads")
PROPOSAL_KEYWORDS = ("proposal", "proposals", "offer")
INVOICE_KEYWORDS = ("invoice", "invoices", "payment")
WEBSITE_KEYWORDS = ("website", "site", "landing page", "page")
BRAND_OS_KEYWORDS = ("brand os", "brand strategy", "positioning", "messaging")
IMAGE_ATTACHMENT_CONTENT_TYPE_PREFIX = "image/"
IMAGE_ATTACHMENT_MAX_FOR_MODEL = 3
IMAGE_ATTACHMENT_URL_TTL_SECONDS = 900


def get_openai_tools(allowed_tool_names: set[str] | None = None) -> list[dict]:
    """Build OpenAI-compatible tools list from registry."""
    tools = []
    for name, tool_def in REGISTRY.items():
        if allowed_tool_names is not None and name not in allowed_tool_names:
            continue
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.parameters_schema,
                },
            }
        )
    return tools


def _estimate_tokens(text: str) -> int:
    """Estimate token count using ~4 chars per token heuristic."""
    return max(1, len(text) // 4)


def _trim_messages_to_token_budget(
    messages: list[dict], max_tokens: int = 6000
) -> list[dict]:
    """
    Trim conversation history to fit within an approximate token budget.
    Walks backwards through messages (newest first) to preserve the most
    recent context. Falls back gracefully if all messages exceed budget.
    """
    result: list[dict] = []
    total = 0
    for msg in reversed(messages):
        estimated = _estimate_tokens(msg.get("content", "") or "")
        if total + estimated > max_tokens and result:
            break
        result.insert(0, msg)
        total += estimated
    return result


def _attachment_text_excerpt(text: str | None, max_chars: int) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    return cleaned[: max(200, max_chars)]


def _is_image_attachment(content_type: str | None) -> bool:
    return bool(content_type and content_type.lower().startswith(IMAGE_ATTACHMENT_CONTENT_TYPE_PREFIX))


def _serialize_attachment_snapshot(
    attachment,
    excerpt_chars: int,
) -> dict:
    content_type = getattr(attachment, "content_type", None)
    image_url: str | None = None
    storage_key = getattr(attachment, "storage_key", None)
    if _is_image_attachment(content_type) and isinstance(storage_key, str) and storage_key:
        try:
            image_url = get_presigned_url(storage_key, expires_in=IMAGE_ATTACHMENT_URL_TTL_SECONDS)
        except Exception as e:
            logger.warning("chat_attachment_presign_failed | attachment_id=%s | error=%s", attachment.id, e)

    excerpt = _attachment_text_excerpt(getattr(attachment, "text_content", None), excerpt_chars)
    return {
        "id": str(attachment.id),
        "file_name": attachment.file_name,
        "content_type": content_type,
        "size_bytes": attachment.size_bytes,
        "has_image_content": bool(image_url),
        "image_url": image_url,
        "has_text_content": bool(excerpt),
        "text_excerpt": excerpt,
    }


def _resolve_attachment_snapshots(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    attachment_ids: list[UUID] | None,
    max_per_message: int,
    excerpt_chars: int,
) -> list[dict]:
    if not attachment_ids:
        return []

    from app.modules.chat.models import ChatAttachment

    ordered_ids: list[UUID] = []
    seen: set[UUID] = set()
    for attachment_id in attachment_ids:
        if attachment_id in seen:
            continue
        seen.add(attachment_id)
        ordered_ids.append(attachment_id)
    ordered_ids = ordered_ids[: max(1, max_per_message)]
    if not ordered_ids:
        return []

    rows = (
        db.query(ChatAttachment)
        .filter(
            ChatAttachment.id.in_(ordered_ids),
            ChatAttachment.user_id == user_id,
            ChatAttachment.conversation_id == conversation_id,
        )
        .all()
    )
    row_map = {row.id: row for row in rows}
    snapshots: list[dict] = []
    for attachment_id in ordered_ids:
        row = row_map.get(attachment_id)
        if not row:
            raise ValueError("Attachment not found in this conversation")
        snapshots.append(_serialize_attachment_snapshot(row, excerpt_chars=excerpt_chars))
    return snapshots


def _build_attachment_context(attachments: list[dict] | None, max_chars: int) -> str | None:
    if not attachments:
        return None
    lines = ["Attached files:"]
    used = 0
    for item in attachments:
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("file_name") or "attachment")
        content_type = item.get("content_type")
        size_bytes = item.get("size_bytes")
        meta_parts = [part for part in [content_type, f"{size_bytes} bytes" if isinstance(size_bytes, int) else None] if part]
        meta = f" ({', '.join(meta_parts)})" if meta_parts else ""
        lines.append(f"- {file_name}{meta}")

        excerpt = item.get("text_excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            remaining = max_chars - used
            if remaining <= 0:
                continue
            clipped = excerpt.strip()[:remaining]
            if clipped:
                used += len(clipped)
                lines.append(f"  Excerpt:\n{clipped}")
    if len(lines) <= 1:
        return None
    return "\n".join(lines)


def _merge_content_with_attachments(
    content: str | None,
    attachments: list[dict] | None,
    max_attachment_chars: int,
) -> str:
    base = (content or "").strip()
    attachment_context = _build_attachment_context(attachments, max_attachment_chars)
    if not attachment_context:
        return base
    if not base:
        return attachment_context
    return f"{base}\n\n{attachment_context}"


def _collect_attachment_image_urls(
    attachments: list[dict] | None,
    max_images: int = IMAGE_ATTACHMENT_MAX_FOR_MODEL,
) -> list[str]:
    if not attachments:
        return []
    urls: list[str] = []
    for item in attachments:
        if not isinstance(item, dict):
            continue
        image_url = item.get("image_url")
        if isinstance(image_url, str) and image_url.strip():
            urls.append(image_url.strip())
        if len(urls) >= max(1, max_images):
            break
    return urls


def _merge_image_urls(
    primary_urls: list[str] | None,
    additional_urls: list[str] | None,
    max_images: int = IMAGE_ATTACHMENT_MAX_FOR_MODEL,
) -> list[str]:
    merged: list[str] = []
    for source in (primary_urls or [], additional_urls or []):
        if not isinstance(source, str):
            continue
        cleaned = source.strip()
        if not cleaned or cleaned in merged:
            continue
        merged.append(cleaned)
        if len(merged) >= max(1, max_images):
            break
    return merged


def _build_user_message_for_model(
    content: str | None,
    attachments: list[dict] | None,
    max_attachment_chars: int,
    additional_image_urls: list[str] | None = None,
) -> dict:
    merged_content = _merge_content_with_attachments(
        content,
        attachments,
        max_attachment_chars,
    )
    image_urls = _merge_image_urls(
        _collect_attachment_image_urls(
            attachments,
            max_images=IMAGE_ATTACHMENT_MAX_FOR_MODEL,
        ),
        additional_image_urls,
        max_images=IMAGE_ATTACHMENT_MAX_FOR_MODEL,
    )
    if not image_urls:
        return {"role": "user", "content": merged_content}

    text = merged_content or "Use the attached images as context."
    parts: list[dict] = [{"type": "text", "text": text}]
    for url in image_urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return {"role": "user", "content": parts}


def build_system_message(
    pack_context: dict | None,
    reference_context: str | None = None,
) -> str:
    """Build system prompt with optional pack context so Klaro is pack-aware."""
    base = (
        "You are Klaro, Klarnow's AI marketing strategist.\n\n"
        "Personality: Direct, expert, concise. You give clear recommendations — not endless lists of options. "
        "You cut through the noise and tell users what to do next.\n\n"
        "Non-negotiable rules:\n"
        "- ONE CTA per campaign, always. If the user suggests multiple CTAs, push back and explain why.\n"
        "- Never promise revenue outcomes ('you'll make $X', 'guaranteed results'). "
        "Reframe as 'conversion-optimized' or 'highest-performing setup'.\n"
        "- Keep all copy specific to the brand — no generic filler text.\n"
        "- Leads, follow-up queues, proposals, invoices, Brand OS, campaigns, and websites are in scope.\n"
        "- For data/list/state questions, use read tools first before answering.\n"
        "- In pack conversations, default to current pack scope unless user explicitly asks for account-wide scope.\n"
    )
    if pack_context:
        base += (
            "\nCurrent pack context:\n"
            + json.dumps(pack_context, indent=2)
            + "\n\nUse this context to give relevant, pack-specific answers. "
            "When the user asks to generate or change something, use the appropriate tool (e.g. generate_brand_os). "
            "Tools create new versions (e.g. Version B); they never overwrite existing versions."
        )
    else:
        base += (
            "\nNo pack is selected. You can answer general marketing questions. "
            "For pack-specific data or edits, identify the target pack or use account-wide scope if requested."
        )
    if reference_context:
        base += (
            "\n\nGlobal reference document excerpts:\n"
            + reference_context
            + "\n\nUse this document context when relevant. "
            "If the user asks beyond what the document covers, you may still answer using general expertise."
        )
    base += (
        "\n\nFormat replies in markdown when helpful (lists, **bold**, headings). "
        "Keep responses concise and action-oriented."
    )
    return base


def _get_reference_context(query: str) -> tuple[str | None, list[dict]]:
    """Retrieve optional global markdown KB context for a user query."""
    if not query.strip():
        return None, []
    try:
        payload = get_reference_kb().retrieve(query)
    except Exception as e:
        logger.warning("chat_reference_retrieval_failed | error=%s", e)
        return None, []
    context_text = payload.get("context_text") if isinstance(payload, dict) else None
    references = payload.get("references") if isinstance(payload, dict) else None
    if not isinstance(context_text, str):
        context_text = None
    if not isinstance(references, list):
        references = []
    return context_text, references


def _parse_tool_args(arguments: str) -> dict:
    try:
        return json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        return {}


def _wants_account_scope(text: str) -> bool:
    if not text.strip():
        return False
    return any(pattern.search(text) for pattern in ACCOUNT_SCOPE_PATTERNS)


def _allowed_tool_names(allow_account_scope: bool) -> set[str]:
    if allow_account_scope:
        return set(REGISTRY.keys())
    return {name for name in REGISTRY.keys() if name not in ACCOUNT_SCOPE_TOOL_NAMES}


def _tool_name_used(tool_calls: list[dict] | None, tool_name: str) -> bool:
    if not tool_calls:
        return False
    for tc in tool_calls:
        fn = tc.get("function", {}) if isinstance(tc, dict) else {}
        if fn.get("name") == tool_name:
            return True
    return False


def _pack_route(pack_id: UUID, suffix: str) -> str:
    return f"/packs/{pack_id}{suffix}"


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _build_action_chips(
    user_content: str,
    pack_id: UUID | None,
    tool_calls: list[dict] | None = None,
    allow_account_scope: bool = False,
) -> list[dict]:
    """Build at most one deterministic redirect chip from intent + scope."""
    text = (user_content or "").lower()

    if allow_account_scope and _wants_account_scope(user_content):
        return [{"label": "Open packs", "href": "/packs"}]

    if allow_account_scope and _tool_name_used(tool_calls, "get_account_snapshot"):
        return [{"label": "Open packs", "href": "/packs"}]

    if pack_id is None:
        if allow_account_scope and _wants_account_scope(user_content):
            return [{"label": "Open packs", "href": "/packs"}]
        return []

    if _has_any(text, FOLLOWUP_KEYWORDS) or _tool_name_used(tool_calls, "get_pack_followup_queue"):
        return [
            {
                "label": "Open Follow-up queue",
                "href": _pack_route(pack_id, "?step=9"),
            }
        ]
    if _has_any(text, LEADS_KEYWORDS):
        return [{"label": "Open Leads", "href": _pack_route(pack_id, "/leads")}]
    if _has_any(text, PROPOSAL_KEYWORDS):
        return [{"label": "Open Proposals", "href": _pack_route(pack_id, "/proposal")}]
    if _has_any(text, INVOICE_KEYWORDS):
        return [{"label": "Open Invoices", "href": _pack_route(pack_id, "/invoice")}]
    if _has_any(text, WEBSITE_KEYWORDS):
        return [{"label": "Open Website", "href": _pack_route(pack_id, "/website")}]
    if _has_any(text, BRAND_OS_KEYWORDS):
        return [{"label": "Open Brand OS", "href": _pack_route(pack_id, "/brand-os")}]
    return []


def execute_tool_calls(
    tool_calls: list[dict],
    pack_id: UUID | None,
    db: Session,
    user_id: UUID,
    allow_account_scope: bool = False,
    agent: str = "orchestrator",
) -> list[dict]:
    """Execute tool calls with pack/account scope enforcement and ownership checks."""
    results = []
    for tc in tool_calls:
        tcid = tc.get("id") or tc.get("tool_call_id")
        fn = tc.get("function", {})
        name = fn.get("name")
        args = _parse_tool_args(fn.get("arguments") or "{}")
        if not name or name not in REGISTRY:
            results.append({"tool_call_id": tcid, "error": f"Unknown tool: {name}"})
            continue

        if name in ACCOUNT_SCOPE_TOOL_NAMES:
            if not allow_account_scope:
                results.append(
                    {
                        "tool_call_id": tcid,
                        "error": "Account-wide scope is disabled for this message",
                    }
                )
                continue
            args["user_id"] = str(user_id)
        else:
            if pack_id is not None:
                # Pack-scoped chat always pins pack_id to current conversation pack.
                args["pack_id"] = str(pack_id)

        pack_id_for_log = pack_id
        pack_arg = args.get("pack_id")
        if pack_arg is not None:
            try:
                pack_uuid = UUID(str(pack_arg))
            except ValueError:
                results.append({"tool_call_id": tcid, "error": "Invalid pack_id"})
                continue
            if not get_pack_for_user(db, pack_uuid, user_id):
                results.append({"tool_call_id": tcid, "error": "Pack not found or access denied"})
                continue
            args["pack_id"] = str(pack_uuid)
            pack_id_for_log = pack_uuid

        try:
            out = execute(name, agent, pack_id_for_log, args, db)
            results.append({"tool_call_id": tcid, "result": out})
        except Exception as e:
            results.append({"tool_call_id": tcid, "error": str(e)})
    return results


def run_chat_turn(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    pack_id: UUID | None,
    user_content: str,
    mode: str = "use",
    apply_to_message_id: UUID | None = None,
    attachment_ids: list[UUID] | None = None,
):
    """
    Run one chat turn: add user message, call LLM (with optional tool_calls), handle Preview/Use/Apply.
    mode: "use" | "preview" | "apply"
    - use: execute tools and return final assistant reply
    - preview: return proposed tool_calls without executing
    - apply: execute tool_calls from the message apply_to_message_id
    Returns: dict with assistant_content, tool_calls (if any), tool_results (if executed), preview (bool)
    """
    from app.modules.chat.models import Conversation, Message

    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        raise ValueError("Conversation not found")

    allow_account_scope = _wants_account_scope(user_content)
    settings = get_settings()
    attachment_snapshots = _resolve_attachment_snapshots(
        db=db,
        user_id=user_id,
        conversation_id=conversation_id,
        attachment_ids=attachment_ids,
        max_per_message=settings.chat_attachment_max_per_message,
        excerpt_chars=settings.chat_attachment_prompt_max_chars,
    )

    # Load recent messages then trim to token budget
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(CHAT_CONTEXT_LAST_N_MESSAGES)
        .all()
    )
    messages = list(reversed(messages))  # chronological

    # Add new user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_content,
        attachments=attachment_snapshots or None,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    pack_context = (
        assemble_context(pack_id, db, day_context=conv.day_context)
        if pack_id
        else None
    )

    # Apply: execute tool_calls from a previous preview message
    if mode == "apply" and apply_to_message_id:
        prev = db.query(Message).filter(
            Message.id == apply_to_message_id,
            Message.conversation_id == conversation_id,
            Message.is_preview.is_(True),
        ).first()
        if not prev or not prev.tool_calls:
            raise ValueError("No preview message or tool_calls to apply")

        tool_calls_list = prev.tool_calls if isinstance(prev.tool_calls, list) else []
        allow_scope_for_apply = allow_account_scope or _tool_name_used(
            tool_calls_list, "get_account_snapshot"
        )
        results = execute_tool_calls(
            tool_calls_list,
            pack_id,
            db,
            user_id=user_id,
            allow_account_scope=allow_scope_for_apply,
        )
        action_chips = _build_action_chips(
            user_content=user_content,
            pack_id=pack_id,
            tool_calls=tool_calls_list,
            allow_account_scope=allow_scope_for_apply,
        )
        tool_results_payload: dict = {"results": results}
        if action_chips:
            tool_results_payload["actions"] = action_chips

        apply_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="Applied the requested changes.",
            tool_calls=prev.tool_calls,
            tool_results=tool_results_payload,
            is_preview=False,
        )
        db.add(apply_msg)
        db.commit()
        db.refresh(apply_msg)
        return {
            "assistant_content": apply_msg.content,
            "message_id": str(apply_msg.id),
            "tool_calls": prev.tool_calls,
            "tool_results": tool_results_payload,
            "action_chips": action_chips,
            "references": [],
            "preview": False,
        }

    reference_context, base_references = _get_reference_context(user_content)
    merged_references = base_references
    effective_user_content = user_content
    retrieved_image_urls: list[str] = []
    system_content = build_system_message(
        pack_context,
        reference_context=reference_context,
    )
    openai_tools = get_openai_tools(_allowed_tool_names(allow_account_scope))

    # Build OpenAI messages with token-aware history trimming
    history_msgs = [
        {
            "role": m.role,
            "content": _merge_content_with_attachments(
                m.content,
                m.attachments if m.role == "user" and isinstance(m.attachments, list) else None,
                settings.chat_attachment_prompt_max_chars,
            ),
        }
        for m in messages
    ]
    history_msgs = _trim_messages_to_token_budget(history_msgs, max_tokens=6000)
    openai_messages = [{"role": "system", "content": system_content}] + history_msgs
    openai_messages.append(
        _build_user_message_for_model(
            effective_user_content,
            attachment_snapshots,
            settings.chat_attachment_prompt_max_chars,
            additional_image_urls=retrieved_image_urls,
        )
    )

    if not settings.openai_api_key:
        # Stub: no LLM
        stub_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="OpenAI API key not configured; chat is disabled.",
        )
        db.add(stub_msg)
        db.commit()
        db.refresh(stub_msg)
        return {
            "assistant_content": stub_msg.content,
            "message_id": str(stub_msg.id),
            "references": merged_references,
            "preview": False,
        }

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=openai_messages,  # pyright: ignore[reportArgumentType]
        tools=openai_tools if openai_tools else None,  # pyright: ignore[reportArgumentType]
        tool_choice="auto" if openai_tools else None,  # pyright: ignore[reportArgumentType]
    )
    choice = response.choices[0] if response.choices else None
    if not choice or not choice.message:
        return {
            "assistant_content": "",
            "message_id": None,
            "references": merged_references,
            "preview": False,
        }

    msg = choice.message
    tool_calls_raw = getattr(msg, "tool_calls", None) or []

    # Preview: return tool_calls without executing
    if mode == "preview" and tool_calls_raw:
        tool_calls_payload = [
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function"),
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls_raw
        ]
        preview_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=msg.content or "Proposed changes (preview):",
            tool_calls=tool_calls_payload,
            is_preview=True,
        )
        db.add(preview_msg)
        db.commit()
        db.refresh(preview_msg)
        return {
            "assistant_content": preview_msg.content,
            "message_id": str(preview_msg.id),
            "tool_calls": tool_calls_payload,
            "references": merged_references,
            "preview": True,
        }

    # Use: execute tool_calls then optionally get final reply
    if tool_calls_raw and mode == "use":
        tool_calls_payload = [
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function"),
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls_raw
        ]
        results = execute_tool_calls(
            tool_calls_payload,
            pack_id,
            db,
            user_id=user_id,
            allow_account_scope=allow_account_scope,
        )

        # Append tool results and call LLM again for final summary
        openai_messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": tool_calls_payload,
            }
        )  # pyright: ignore[reportArgumentType]
        for r in results:
            openai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": r.get("tool_call_id") or "unknown",
                    "content": json.dumps(r.get("result") or r),
                }
            )
        follow_up = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,  # pyright: ignore[reportArgumentType]
        )
        follow_msg_content = ""
        if follow_up.choices and follow_up.choices[0].message:
            follow_msg_content = follow_up.choices[0].message.content or ""

        action_chips = _build_action_chips(
            user_content=user_content,
            pack_id=pack_id,
            tool_calls=tool_calls_payload,
            allow_account_scope=allow_account_scope,
        )
        tool_results_payload: dict = {"results": results}
        if action_chips:
            tool_results_payload["actions"] = action_chips

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=follow_msg_content,
            tool_calls=tool_calls_payload,
            tool_results=tool_results_payload,
            is_preview=False,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        return {
            "assistant_content": assistant_msg.content,
            "message_id": str(assistant_msg.id),
            "tool_calls": tool_calls_payload,
            "tool_results": tool_results_payload,
            "action_chips": action_chips,
            "references": merged_references,
            "preview": False,
        }

    # No tool_calls or simple reply
    action_chips = _build_action_chips(
        user_content=user_content,
        pack_id=pack_id,
        tool_calls=[],
        allow_account_scope=allow_account_scope,
    )
    tool_results_payload = {"actions": action_chips} if action_chips else None

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=msg.content or "",
        tool_results=tool_results_payload,
        is_preview=False,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    out = {
        "assistant_content": assistant_msg.content,
        "message_id": str(assistant_msg.id),
        "references": merged_references,
        "preview": False,
    }
    if tool_results_payload:
        out["tool_results"] = tool_results_payload
    if action_chips:
        out["action_chips"] = action_chips
    return out


def _sse_event(event: str, data: dict) -> str:
    """Format one SSE event: event: name + data: json."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _sse_status(phase: str, label: str) -> str:
    """Format one SSE status event for transient UI state."""
    return _sse_event("status", {"phase": phase, "label": label})


def run_chat_turn_stream(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    pack_id: UUID | None,
    user_content: str,
    mode: str = "use",
    apply_to_message_id: UUID | None = None,
    attachment_ids: list[UUID] | None = None,
):
    """
    Generator that yields SSE events:
    - status: transient phase updates (thinking/tool execution/finalizing/responding)
    - chunk: incremental assistant text deltas
    - done: final payload with message metadata
    - error: recoverable error payload
    """
    from app.modules.chat.models import Conversation, Message

    try:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        ).first()
        if not conv:
            yield _sse_event("error", {"error": "Conversation not found"})
            return

        # Apply: no model stream; execute preview tool_calls and return done.
        if mode == "apply" and apply_to_message_id:
            yield _sse_status("tool_execution", "Using tools...")
            try:
                result = run_chat_turn(
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    pack_id=pack_id,
                    user_content=user_content,
                    mode="apply",
                    apply_to_message_id=apply_to_message_id,
                    attachment_ids=attachment_ids,
                )
                yield _sse_event("done", result)
            except Exception as e:
                yield _sse_event("error", {"error": str(e)})
            return

        allow_account_scope = _wants_account_scope(user_content)
        settings = get_settings()
        attachment_snapshots = _resolve_attachment_snapshots(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            attachment_ids=attachment_ids,
            max_per_message=settings.chat_attachment_max_per_message,
            excerpt_chars=settings.chat_attachment_prompt_max_chars,
        )

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(CHAT_CONTEXT_LAST_N_MESSAGES)
            .all()
        )
        messages = list(reversed(messages))

        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_content,
            attachments=attachment_snapshots or None,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        pack_context = (
            assemble_context(pack_id, db, day_context=conv.day_context)
            if pack_id
            else None
        )
        reference_context, base_references = _get_reference_context(user_content)
        merged_references = base_references
        effective_user_content = user_content
        retrieved_image_urls: list[str] = []
        system_content = build_system_message(
            pack_context,
            reference_context=reference_context,
        )
        openai_tools = get_openai_tools(_allowed_tool_names(allow_account_scope))

        history_msgs = [
            {
                "role": m.role,
                "content": _merge_content_with_attachments(
                    m.content,
                    m.attachments if m.role == "user" and isinstance(m.attachments, list) else None,
                    settings.chat_attachment_prompt_max_chars,
                ),
            }
            for m in messages
        ]
        history_msgs = _trim_messages_to_token_budget(history_msgs, max_tokens=6000)
        openai_messages = [{"role": "system", "content": system_content}] + history_msgs
        openai_messages.append(
            _build_user_message_for_model(
                effective_user_content,
                attachment_snapshots,
                settings.chat_attachment_prompt_max_chars,
                additional_image_urls=retrieved_image_urls,
            )
        )

        yield _sse_status("thinking", "Thinking...")

        if not settings.openai_api_key:
            stub_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content="OpenAI API key not configured; chat is disabled.",
            )
            db.add(stub_msg)
            db.commit()
            db.refresh(stub_msg)
            yield _sse_event(
                "done",
                {
                    "assistant_content": stub_msg.content,
                    "message_id": str(stub_msg.id),
                    "references": merged_references,
                    "preview": False,
                },
            )
            return

        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,  # pyright: ignore[reportArgumentType]
            tools=openai_tools if openai_tools else None,  # pyright: ignore[reportArgumentType]
            tool_choice="auto" if openai_tools else None,  # pyright: ignore[reportArgumentType]
            stream=True,
        )

        content_parts: list[str] = []
        # index -> {id, type, function: {name, arguments}}
        tool_calls_accum: dict[int, dict] = {}
        emitted_responding = False

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None) and delta.content:
                if not emitted_responding:
                    emitted_responding = True
                    yield _sse_status("responding", "Responding...")
                content_parts.append(delta.content)
                yield _sse_event("chunk", {"delta": delta.content})
            tool_calls_delta = getattr(delta, "tool_calls", None) or []
            for tc in tool_calls_delta:
                idx = getattr(tc, "index", 0)
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {
                        "id": getattr(tc, "id", "") or "",
                        "type": getattr(tc, "type", "function") or "function",
                        "function": {"name": "", "arguments": ""},
                    }
                if getattr(tc, "id", None):
                    tool_calls_accum[idx]["id"] = tc.id
                if getattr(tc, "type", None):
                    tool_calls_accum[idx]["type"] = tc.type
                fn = getattr(tc, "function", None)
                if fn:
                    if getattr(fn, "name", None):
                        tool_calls_accum[idx]["function"]["name"] = fn.name
                    if getattr(fn, "arguments", None):
                        tool_calls_accum[idx]["function"]["arguments"] += fn.arguments

        full_content = "".join(content_parts)
        tool_calls_list = [tool_calls_accum[i] for i in sorted(tool_calls_accum.keys())]
        tool_calls_raw = tool_calls_list  # list of dicts in our format

        # Preview: persist with tool_calls, yield done.
        if mode == "preview" and tool_calls_raw:
            preview_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_content or "Proposed changes (preview):",
                tool_calls=tool_calls_raw,
                is_preview=True,
            )
            db.add(preview_msg)
            db.commit()
            db.refresh(preview_msg)
            yield _sse_event(
                "done",
                {
                    "assistant_content": preview_msg.content,
                    "message_id": str(preview_msg.id),
                    "tool_calls": tool_calls_raw,
                    "references": merged_references,
                    "preview": True,
                },
            )
            return

        # Use: execute tools, stream follow-up summary, persist, yield done.
        if tool_calls_raw and mode == "use":
            tool_calls_payload = [
                {
                    "id": tc.get("id", ""),
                    "type": tc.get("type", "function"),
                    "function": tc.get("function", {"name": "", "arguments": "{}"}),
                }
                for tc in tool_calls_raw
            ]
            yield _sse_status("tool_execution", "Using tools...")
            results = execute_tool_calls(
                tool_calls_payload,
                pack_id,
                db,
                user_id=user_id,
                allow_account_scope=allow_account_scope,
            )
            openai_messages.append(
                {
                    "role": "assistant",
                    "content": full_content or "",
                    "tool_calls": tool_calls_payload,
                }
            )  # pyright: ignore[reportArgumentType]
            for r in results:
                openai_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": r.get("tool_call_id") or "unknown",
                        "content": json.dumps(r.get("result") or r),
                    }
                )

            yield _sse_status("finalizing", "Finalizing answer...")
            follow_up_stream = client.chat.completions.create(
                model="gpt-4o",
                messages=openai_messages,  # pyright: ignore[reportArgumentType]
                stream=True,
            )
            follow_parts: list[str] = []
            follow_emitted_responding = False
            for follow_chunk in follow_up_stream:
                if not follow_chunk.choices:
                    continue
                follow_delta = follow_chunk.choices[0].delta
                if getattr(follow_delta, "content", None) and follow_delta.content:
                    if not follow_emitted_responding:
                        follow_emitted_responding = True
                        yield _sse_status("responding", "Responding...")
                    follow_parts.append(follow_delta.content)
                    yield _sse_event("chunk", {"delta": follow_delta.content})

            follow_msg_content = "".join(follow_parts)
            action_chips = _build_action_chips(
                user_content=user_content,
                pack_id=pack_id,
                tool_calls=tool_calls_payload,
                allow_account_scope=allow_account_scope,
            )
            tool_results_payload: dict = {"results": results}
            if action_chips:
                tool_results_payload["actions"] = action_chips

            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=follow_msg_content,
                tool_calls=tool_calls_payload,
                tool_results=tool_results_payload,
                is_preview=False,
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            yield _sse_event(
                "done",
                {
                    "assistant_content": assistant_msg.content,
                    "message_id": str(assistant_msg.id),
                    "tool_calls": tool_calls_payload,
                    "tool_results": tool_results_payload,
                    "action_chips": action_chips,
                    "references": merged_references,
                    "preview": False,
                },
            )
            return

        # Simple reply: persist, yield done.
        action_chips = _build_action_chips(
            user_content=user_content,
            pack_id=pack_id,
            tool_calls=[],
            allow_account_scope=allow_account_scope,
        )
        tool_results_payload = {"actions": action_chips} if action_chips else None
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_content,
            tool_results=tool_results_payload,
            is_preview=False,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        done_payload = {
            "assistant_content": assistant_msg.content,
            "message_id": str(assistant_msg.id),
            "references": merged_references,
            "preview": False,
        }
        if tool_results_payload:
            done_payload["tool_results"] = tool_results_payload
        if action_chips:
            done_payload["action_chips"] = action_chips
        yield _sse_event("done", done_payload)
    except Exception as e:
        yield _sse_event("error", {"error": str(e)})
