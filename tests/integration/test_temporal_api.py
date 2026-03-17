"""Integration tests for the temporal analysis API endpoints.

These tests exercise /api/temporal/* via the FastAPI TestClient with a
seeded graph containing dated relationships (TRANSFERRED_TO with dates).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client(seeded_graph) -> TestClient:
    """Return a TestClient backed by a seeded graph."""
    from src.main import app

    return TestClient(app)


class TestGraphAtTime:
    """Tests for GET /api/temporal/graph-at."""

    def test_graph_at_date(self, client: TestClient):
        resp = client.get("/api/temporal/graph-at", params={"date": "2024-01-16"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_graph_at_date_with_entity(self, client: TestClient):
        resp = client.get(
            "/api/temporal/graph-at", params={"date": "2024-01-16", "entity_id": "test-a1"}
        )
        assert resp.status_code == 200

    def test_graph_at_date_with_limit(self, client: TestClient):
        resp = client.get("/api/temporal/graph-at", params={"date": "2024-01-16", "limit": 5})
        assert resp.status_code == 200

    def test_graph_at_requires_date(self, client: TestClient):
        resp = client.get("/api/temporal/graph-at")
        assert resp.status_code == 422

    def test_graph_at_future_date(self, client: TestClient):
        resp = client.get("/api/temporal/graph-at", params={"date": "2099-01-01"})
        assert resp.status_code == 200


class TestChangesBetween:
    """Tests for GET /api/temporal/changes."""

    def test_changes_in_range(self, client: TestClient):
        resp = client.get(
            "/api/temporal/changes", params={"start": "2024-01-01", "end": "2024-02-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_changes_narrow_range(self, client: TestClient):
        resp = client.get(
            "/api/temporal/changes", params={"start": "2024-01-15", "end": "2024-01-16"}
        )
        assert resp.status_code == 200

    def test_changes_empty_range(self, client: TestClient):
        resp = client.get(
            "/api/temporal/changes", params={"start": "2000-01-01", "end": "2000-02-01"}
        )
        assert resp.status_code == 200

    def test_changes_requires_both_dates(self, client: TestClient):
        resp = client.get("/api/temporal/changes", params={"start": "2024-01-01"})
        assert resp.status_code == 422


class TestRelationshipTimeline:
    """Tests for GET /api/temporal/timeline."""

    def test_full_timeline(self, client: TestClient):
        resp = client.get("/api/temporal/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_timeline_with_limit(self, client: TestClient):
        resp = client.get("/api/temporal/timeline", params={"limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


class TestDateRange:
    """Tests for GET /api/temporal/date-range."""

    def test_date_range(self, client: TestClient):
        resp = client.get("/api/temporal/date-range")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


class TestEntityTemporalProfile:
    """Tests for GET /api/temporal/entity/{entity_id}."""

    def test_profile_for_account(self, client: TestClient):
        resp = client.get("/api/temporal/entity/test-a1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_profile_with_limit(self, client: TestClient):
        resp = client.get("/api/temporal/entity/test-a1", params={"limit": 5})
        assert resp.status_code == 200

    def test_profile_nonexistent_entity(self, client: TestClient):
        resp = client.get("/api/temporal/entity/no-such-entity")
        assert resp.status_code == 200
