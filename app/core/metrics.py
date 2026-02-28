"""In-process request metrics for lightweight observability."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class MetricsSnapshot:
    total_requests: int
    error_requests: int
    avg_duration_ms: float
    routes: dict[str, int]


_total_requests = 0
_error_requests = 0
_total_duration_ms = 0.0
_route_counts: dict[str, int] = defaultdict(int)


def record_request(path: str, status_code: int, duration_ms: float) -> None:
    global _total_requests, _error_requests, _total_duration_ms
    _total_requests += 1
    _total_duration_ms += duration_ms
    if status_code >= 500:
        _error_requests += 1
    _route_counts[path] += 1


def snapshot() -> MetricsSnapshot:
    avg = _total_duration_ms / _total_requests if _total_requests else 0.0
    return MetricsSnapshot(
        total_requests=_total_requests,
        error_requests=_error_requests,
        avg_duration_ms=round(avg, 2),
        routes=dict(_route_counts),
    )

