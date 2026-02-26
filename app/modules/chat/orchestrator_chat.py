"""Chat turn: LLM with pack context and tool calling; Use / Preview / Apply."""

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.agents.orchestrator import assemble_context, CHAT_CONTEXT_LAST_N_MESSAGES
from app.modules.agents.registry import REGISTRY, execute


def get_openai_tools() -> list[dict]:
    """Build OpenAI-compatible tools list from registry."""
    tools = []
    for name, tool_def in REGISTRY.items():
        tools.append({
            "type": "function",
            "function": {
                "name": tool_def.name,
                "description": tool_def.description,
                "parameters": tool_def.parameters_schema,
            },
        })
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


def build_system_message(pack_context: dict | None) -> str:
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
        "- If asked to do something outside Brand OS / campaigns / conversion pages / creatives, "
        "redirect: 'I'm specialized in marketing execution — let me help you with [X] instead.'\n"
    )
    if pack_context:
        base += (
            "\nCurrent pack context:\n"
            + json.dumps(pack_context, indent=2)
            + "\n\nUse this context to give relevant, pack-specific answers. "
            "When the user asks to generate or change something, use the appropriate tool (e.g. generate_brand_os). "
            "Tools create new versions (e.g. Version B); they never overwrite existing versions."
        )
        if "day_context" in pack_context and pack_context.get("day_context") is not None:
            day_n = pack_context["day_context"]
            day_title = pack_context.get("day_title", "Day")
            day_win = pack_context.get("day_win_condition", "")
            base += (
                f"\n\n--- Day {day_n} Conversational Flow ---\n"
                f"You are guiding the user through Day {day_n}: {day_title}. "
                f"Win condition: {day_win}.\n"
                "Follow these steps in order. Ask ONE question at a time. "
                "When asking a question, ALWAYS call ask_day_question with field_key and day_context so the user gets input guidance and suggestion chips. "
                "After the user answers, move to the next step. "
                "When the user asks for different suggestions (e.g. 'suggest more', 'other options', 'different ideas'), call ask_day_question with re_suggest=true and previous_chips=[labels they already saw]. "
                "When the user has provided the required information, call update_pack to save it.\n"
            )
            steps = pack_context.get("day_conversation_steps", [])
            if steps:
                base += "Steps (ask one at a time):\n"
                for s in steps:
                    if s.get("if_has_brand"):
                        base += f"  - {s['key']}: {s['label']} (only if has_existing_brand is Yes)\n"
                    else:
                        base += f"  - {s['key']}: {s['label']}\n"
            base += (
                "\nWhen the win condition is met and data is saved, call complete_sprint_day to mark the day complete. "
                "After calling complete_sprint_day: PAUSE. Tell the user they've completed the day, congratulate them, "
                "and ask if they want to proceed to the next day. Wait for their confirmation (e.g. 'Yes', 'Let's go') "
                "before offering to start the next day."
            )
    else:
        base += (
            "\nNo pack is selected. You can answer general marketing questions. "
            "To generate or change pack content, the user must be in a pack-scoped conversation."
        )
    base += (
        "\n\nFormat replies in markdown when helpful (lists, **bold**, headings). "
        "Keep responses concise and action-oriented."
    )
    return base


def _parse_tool_args(arguments: str) -> dict:
    try:
        return json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        return {}


def execute_tool_calls(
    tool_calls: list[dict],
    pack_id: UUID | None,
    db: Session,
    agent: str = "orchestrator",
) -> list[dict]:
    """Execute a list of OpenAI-format tool_calls and return results (for Use/Apply)."""
    results = []
    for tc in tool_calls:
        tcid = tc.get("id") or tc.get("tool_call_id")
        fn = tc.get("function", {})
        name = fn.get("name")
        args = _parse_tool_args(fn.get("arguments") or "{}")
        if not name or name not in REGISTRY:
            results.append({"tool_call_id": tcid, "error": f"Unknown tool: {name}"})
            continue
        if pack_id and "pack_id" not in args:
            args["pack_id"] = str(pack_id)
        try:
            out = execute(name, agent, pack_id, args, db)
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
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    pack_context = (
        assemble_context(pack_id, db, day_context=conv.day_context)
        if pack_id
        else None
    )
    system_content = build_system_message(pack_context)
    openai_tools = get_openai_tools()
    settings = get_settings()

    # Apply: execute tool_calls from a previous preview message
    if mode == "apply" and apply_to_message_id:
        prev = db.query(Message).filter(
            Message.id == apply_to_message_id,
            Message.conversation_id == conversation_id,
            Message.is_preview.is_(True),
        ).first()
        if not prev or not prev.tool_calls:
            raise ValueError("No preview message or tool_calls to apply")
        # OpenAI format: list of {id, type, function: {name, arguments}}
        tool_calls_list = prev.tool_calls if isinstance(prev.tool_calls, list) else []
        results = execute_tool_calls(tool_calls_list, pack_id, db)
        # Store tool results on a new assistant message
        apply_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="Applied the requested changes.",
            tool_calls=prev.tool_calls,
            tool_results={"results": results},
            is_preview=False,
        )
        db.add(apply_msg)
        db.commit()
        db.refresh(apply_msg)
        return {
            "assistant_content": apply_msg.content,
            "message_id": str(apply_msg.id),
            "tool_calls": prev.tool_calls,
            "tool_results": results,
            "preview": False,
        }

    # Build OpenAI messages with token-aware history trimming
    history_msgs = [{"role": m.role, "content": m.content or ""} for m in messages]
    history_msgs = _trim_messages_to_token_budget(history_msgs, max_tokens=6000)
    openai_messages = [{"role": "system", "content": system_content}] + history_msgs
    openai_messages.append({"role": "user", "content": user_content})

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
        return {"assistant_content": stub_msg.content, "message_id": str(stub_msg.id), "preview": False}

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
        return {"assistant_content": "", "message_id": None, "preview": False}

    msg = choice.message
    tool_calls_raw = getattr(msg, "tool_calls", None) or []

    # Preview: return tool_calls without executing
    if mode == "preview" and tool_calls_raw:
        tool_calls_payload = [
            {"id": tc.id, "type": getattr(tc, "type", "function"), "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
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
            "preview": True,
        }

    # Use: execute tool_calls then optionally get final reply
    if tool_calls_raw and mode == "use":
        tool_calls_payload = [
            {"id": tc.id, "type": getattr(tc, "type", "function"), "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in tool_calls_raw
        ]
        results = execute_tool_calls(tool_calls_payload, pack_id, db)

        # Append tool results and call LLM again for final summary
        openai_messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": tool_calls_payload})  # pyright: ignore[reportArgumentType]
        for r in results:
            openai_messages.append({
                "role": "tool",
                "tool_call_id": r.get("tool_call_id") or "unknown",
                "content": json.dumps(r.get("result") or r),
            })
        follow_up = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,  # pyright: ignore[reportArgumentType]
        )
        follow_msg_content = ""
        if follow_up.choices and follow_up.choices[0].message:
            follow_msg_content = follow_up.choices[0].message.content or ""

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=follow_msg_content,
            tool_calls=tool_calls_payload,
            tool_results={"results": results},
            is_preview=False,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        return {
            "assistant_content": assistant_msg.content,
            "message_id": str(assistant_msg.id),
            "tool_calls": tool_calls_payload,
            "tool_results": results,
            "preview": False,
        }

    # No tool_calls or simple reply
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=msg.content or "",
        is_preview=False,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return {
        "assistant_content": assistant_msg.content,
        "message_id": str(assistant_msg.id),
        "preview": False,
    }


def _sse_event(event: str, data: dict) -> str:
    """Format one SSE event: event: name + data: json."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def run_chat_turn_stream(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    pack_id: UUID | None,
    user_content: str,
    mode: str = "use",
    apply_to_message_id: UUID | None = None,
):
    """
    Generator that yields SSE events: chunk (with delta) for each content piece, then done (with message_id, etc.).
    Uses OpenAI stream=True for the first LLM call; follow-up after tool execution is non-streaming.
    """
    from app.modules.chat.models import Conversation, Message

    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        yield _sse_event("error", {"error": "Conversation not found"})
        return

    # Apply: no streaming; run_chat_turn adds user message and does apply
    if mode == "apply" and apply_to_message_id:
        try:
            result = run_chat_turn(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                pack_id=pack_id,
                user_content=user_content,
                mode="apply",
                apply_to_message_id=apply_to_message_id,
            )
            yield _sse_event("done", result)
        except Exception as e:
            yield _sse_event("error", {"error": str(e)})
        return

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
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    pack_context = (
        assemble_context(pack_id, db, day_context=conv.day_context)
        if pack_id
        else None
    )
    system_content = build_system_message(pack_context)
    openai_tools = get_openai_tools()
    settings = get_settings()

    history_msgs = [{"role": m.role, "content": m.content or ""} for m in messages]
    history_msgs = _trim_messages_to_token_budget(history_msgs, max_tokens=6000)
    openai_messages = [{"role": "system", "content": system_content}] + history_msgs
    openai_messages.append({"role": "user", "content": user_content})

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
    tool_calls_accum: dict[int, dict] = {}  # index -> {id, type, function: {name, arguments}}

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None) and delta.content:
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

    # Preview: persist with tool_calls, yield done
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
                "preview": True,
            },
        )
        return

    # Use: execute tools, follow-up call (non-streaming), persist, yield done
    if tool_calls_raw and mode == "use":
        tool_calls_payload = [
            {"id": tc.get("id", ""), "type": tc.get("type", "function"), "function": tc.get("function", {"name": "", "arguments": "{}"})}
            for tc in tool_calls_raw
        ]
        results = execute_tool_calls(tool_calls_payload, pack_id, db)
        openai_messages.append({"role": "assistant", "content": full_content or "", "tool_calls": tool_calls_payload})  # pyright: ignore[reportArgumentType]
        for r in results:
            openai_messages.append({
                "role": "tool",
                "tool_call_id": r.get("tool_call_id") or "unknown",
                "content": json.dumps(r.get("result") or r),
            })
        follow_up = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,  # pyright: ignore[reportArgumentType]
        )
        follow_msg_content = ""
        if follow_up.choices and follow_up.choices[0].message:
            follow_msg_content = follow_up.choices[0].message.content or ""
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=follow_msg_content,
            tool_calls=tool_calls_payload,
            tool_results={"results": results},
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
                "tool_results": results,
                "preview": False,
            },
        )
        return

    # Simple reply: persist, yield done
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=full_content,
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
            "preview": False,
        },
    )
