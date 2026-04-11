"""Unit tests for app.core.metrics module."""

import importlib
import pytest

import app.core.metrics as metrics_mod


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset global metrics state before each test."""
    metrics_mod._total_requests = 0
    metrics_mod._error_requests = 0
    metrics_mod._total_duration_ms = 0.0
    metrics_mod._total_db_queries = 0
    metrics_mod._total_db_query_time_ms = 0.0
    metrics_mod._route_counts.clear()
    yield


class TestRecordRequest:
    def test_increments_total_requests(self):
        metrics_mod.record_request("/health", 200, 10.0)
        assert metrics_mod._total_requests == 1

    def test_increments_error_on_5xx(self):
        metrics_mod.record_request("/api", 500, 50.0)
        assert metrics_mod._error_requests == 1

    def test_does_not_increment_error_on_4xx(self):
        metrics_mod.record_request("/api", 404, 5.0)
        assert metrics_mod._error_requests == 0

    def test_does_not_increment_error_on_2xx(self):
        metrics_mod.record_request("/api", 200, 5.0)
        assert metrics_mod._error_requests == 0

    def test_accumulates_duration(self):
        metrics_mod.record_request("/a", 200, 10.0)
        metrics_mod.record_request("/b", 200, 20.0)
        assert metrics_mod._total_duration_ms == 30.0

    def test_tracks_route_counts(self):
        metrics_mod.record_request("/health", 200, 1.0)
        metrics_mod.record_request("/health", 200, 1.0)
        metrics_mod.record_request("/api", 200, 1.0)
        assert metrics_mod._route_counts["/health"] == 2
        assert metrics_mod._route_counts["/api"] == 1

    def test_accumulates_db_queries(self):
        metrics_mod.record_request("/a", 200, 1.0, db_queries=3, db_query_time_ms=15.0)
        metrics_mod.record_request("/b", 200, 1.0, db_queries=2, db_query_time_ms=10.0)
        assert metrics_mod._total_db_queries == 5
        assert metrics_mod._total_db_query_time_ms == 25.0

    def test_negative_db_queries_clamped_to_zero(self):
        metrics_mod.record_request("/a", 200, 1.0, db_queries=-5)
        assert metrics_mod._total_db_queries == 0

    def test_negative_db_query_time_clamped_to_zero(self):
        metrics_mod.record_request("/a", 200, 1.0, db_query_time_ms=-10.0)
        assert metrics_mod._total_db_query_time_ms == 0.0


class TestSnapshot:
    def test_empty_snapshot(self):
        snap = metrics_mod.snapshot()
        assert snap.total_requests == 0
        assert snap.error_requests == 0
        assert snap.avg_duration_ms == 0.0
        assert snap.total_db_queries == 0
        assert snap.avg_db_queries_per_request == 0.0
        assert snap.avg_db_query_time_ms == 0.0
        assert snap.routes == {}

    def test_snapshot_with_data(self):
        metrics_mod.record_request("/a", 200, 10.0, db_queries=2, db_query_time_ms=5.0)
        metrics_mod.record_request("/b", 500, 30.0, db_queries=4, db_query_time_ms=15.0)
        snap = metrics_mod.snapshot()
        assert snap.total_requests == 2
        assert snap.error_requests == 1
        assert snap.avg_duration_ms == 20.0
        assert snap.total_db_queries == 6
        assert snap.avg_db_queries_per_request == 3.0
        assert snap.avg_db_query_time_ms == 10.0
        assert snap.routes == {"/a": 1, "/b": 1}

    def test_avg_duration_rounds_to_two_decimals(self):
        metrics_mod.record_request("/a", 200, 10.333)
        metrics_mod.record_request("/b", 200, 10.333)
        metrics_mod.record_request("/c", 200, 10.334)
        snap = metrics_mod.snapshot()
        assert snap.avg_duration_ms == 10.33
