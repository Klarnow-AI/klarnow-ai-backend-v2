"""Database package exports.

Keep session/engine imports lazy so metadata-only imports like Alembic's
`app.core.db.base` do not also require async driver dependencies.
"""

from importlib import import_module
from typing import Any

from app.core.db.base import Base

_SESSION_EXPORTS = {
    "get_db",
    "engine",
    "SessionLocal",
    "async_get_db",
    "async_engine",
    "AsyncSessionLocal",
}

__all__ = ["Base", *_SESSION_EXPORTS]


def __getattr__(name: str) -> Any:
    if name in _SESSION_EXPORTS:
        session_module = import_module("app.core.db.session")
        return getattr(session_module, name)
    raise AttributeError(f"module 'app.core.db' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
