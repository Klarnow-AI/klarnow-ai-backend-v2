"""Request- and worker-scoped SQL query counters."""

from __future__ import annotations

from contextvars import ContextVar

_db_query_count: ContextVar[int] = ContextVar("db_query_count", default=0)
_db_query_duration_ms: ContextVar[float] = ContextVar("db_query_duration_ms", default=0.0)


def reset_db_query_stats() -> None:
    _db_query_count.set(0)
    _db_query_duration_ms.set(0.0)


def record_db_query(duration_ms: float) -> None:
    _db_query_count.set(_db_query_count.get() + 1)
    _db_query_duration_ms.set(_db_query_duration_ms.get() + max(0.0, duration_ms))


def get_db_query_count() -> int:
    return _db_query_count.get()


def get_db_query_duration_ms() -> float:
    return round(_db_query_duration_ms.get(), 2)
