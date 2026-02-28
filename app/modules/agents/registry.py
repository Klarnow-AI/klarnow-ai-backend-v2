"""Tool registry: register tools, permission matrix, execute with logging."""

from __future__ import annotations

import copy
import json
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.agents.models import DecisionLog

# Orchestrator can call any tool; specialists are restricted per A-PRD
PERMISSION_MATRIX = {
    "orchestrator": None,  # None = all tools
    "strategy": ["generate_brand_os"],
    "conversion": ["generate_conversion_page"],
    "creative": ["render_poster"],
    "video": ["render_video"],
    "revenue": ["create_proposal", "create_invoice"],
}


class ToolDef:
    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict,
        fn: Callable[..., dict],
        allowed_agents: list[str] | None = None,
        side_effects: str = "writes to database",
    ):
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.fn = fn
        self.allowed_agents = allowed_agents  # if None, only orchestrator
        self.side_effects = side_effects


REGISTRY: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> None:
    REGISTRY[tool.name] = tool


def _sanitise_inputs(inputs: dict) -> dict:
    """Reduce input size for logging; keep structure and ids."""
    out = {}
    for k, v in inputs.items():
        if v is None:
            out[k] = None
        elif isinstance(v, (str, int, bool)):
            s = str(v)
            out[k] = s[:500] + "..." if len(s) > 500 else s
        elif isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, dict):
            out[k] = _sanitise_inputs(v)
        elif isinstance(v, list):
            out[k] = [_sanitise_inputs(x) if isinstance(x, dict) else str(x)[:200] for x in v[:20]]
        else:
            out[k] = str(type(v).__name__)
    return out


def _can_run(agent: str, tool_name: str) -> bool:
    allowed = PERMISSION_MATRIX.get(agent)
    if allowed is None:
        return True
    return tool_name in allowed


def execute(
    tool_name: str,
    agent: str,
    pack_id: UUID | None,
    inputs: dict,
    db: Session,
) -> dict:
    """
    Validate and run a tool with savepoint isolation.

    Transaction policy:
    - Each tool call runs inside a nested transaction (savepoint).
    - Tool success/failure logs are flushed, not committed.
    - The caller owns final commit/rollback for the request.
    """
    if tool_name not in REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")
    if not _can_run(agent, tool_name):
        raise PermissionError(f"Agent {agent} is not allowed to run tool {tool_name}")

    tool = REGISTRY[tool_name]
    sanitised = _sanitise_inputs(copy.deepcopy(inputs))

    try:
        with db.begin_nested():
            result = tool.fn(db=db, **inputs)
            summary = json.dumps(result)[:2000] if result else "ok"
            db.add(
                DecisionLog(
                    tool_name=tool_name,
                    agent=agent,
                    pack_id=pack_id,
                    inputs_sanitized=sanitised,
                    success=True,
                    result_summary=summary,
                )
            )
            db.flush()
            return result
    except Exception as e:
        with db.begin_nested():
            db.add(
                DecisionLog(
                    tool_name=tool_name,
                    agent=agent,
                    pack_id=pack_id,
                    inputs_sanitized=sanitised,
                    success=False,
                    error_message=str(e)[:2000],
                )
            )
            db.flush()
        raise
