"""Tests for API query limit parameters on previously unbounded endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(test_client: TestClient) -> TestClient:
    return test_client


class TestEntityRelationshipsLimit:
    """GET /api/entities/{id}/relationships now accepts a limit parameter."""

    def test_default_limit_is_100(self, client: TestClient):
        """Default limit should be 100."""
        with patch("src.api.entities.queries") as mock_q:
            mock_q.get_entity_any_label.return_value = {"id": "p-1", "label": "Person"}
            mock_q.get_entity_relationships.return_value = []
            resp = client.get("/api/entities/p-1/relationships")
            assert resp.status_code == 200
            mock_q.get_entity_relationships.assert_called_once()
            call_kwargs = mock_q.get_entity_relationships.call_args
            assert call_kwargs.kwargs.get("limit") == 100 or call_kwargs[1].get("limit") == 100

    def test_custom_limit(self, client: TestClient):
        with patch("src.api.entities.queries") as mock_q:
            mock_q.get_entity_any_label.return_value = {"id": "p-1", "label": "Person"}
            mock_q.get_entity_relationships.return_value = []
            resp = client.get("/api/entities/p-1/relationships?limit=10")
            assert resp.status_code == 200

    def test_limit_too_high(self, client: TestClient):
        resp = client.get("/api/entities/p-1/relationships?limit=999")
        assert resp.status_code == 422

    def test_limit_zero(self, client: TestClient):
        resp = client.get("/api/entities/p-1/relationships?limit=0")
        assert resp.status_code == 422


class TestSnapshotsLimit:
    """GET /api/snapshots/ now accepts a limit parameter."""

    def test_default_limit(self, client: TestClient):
        with patch("src.api.snapshots.diff") as mock_diff:
            mock_diff.list_snapshots.return_value = []
            resp = client.get("/api/snapshots/")
            assert resp.status_code == 200
            call_args = mock_diff.list_snapshots.call_args
            assert call_args.kwargs.get("limit") == 100 or (
                len(call_args.args) >= 3 and call_args.args[2] == 100
            )

    def test_custom_limit(self, client: TestClient):
        with patch("src.api.snapshots.diff") as mock_diff:
            mock_diff.list_snapshots.return_value = []
            resp = client.get("/api/snapshots/?limit=5")
            assert resp.status_code == 200

    def test_limit_too_high(self, client: TestClient):
        resp = client.get("/api/snapshots/?limit=501")
        assert resp.status_code == 422


class TestTemporalEntityLimit:
    """GET /api/temporal/entity/{id} now accepts a limit parameter."""

    def test_default_limit(self, client: TestClient):
        with patch("src.api.temporal.temporal") as mock_temporal:
            mock_temporal.get_entity_temporal_profile.return_value = {
                "entity_id": "p-1",
                "events": [],
                "total_events": 0,
                "active_periods": [],
            }
            resp = client.get("/api/temporal/entity/p-1")
            assert resp.status_code == 200
            call_args = mock_temporal.get_entity_temporal_profile.call_args
            assert call_args.kwargs.get("limit") == 200 or (
                len(call_args.args) >= 3 and call_args.args[2] == 200
            )

    def test_custom_limit(self, client: TestClient):
        with patch("src.api.temporal.temporal") as mock_temporal:
            mock_temporal.get_entity_temporal_profile.return_value = {
                "entity_id": "p-1",
                "events": [],
                "total_events": 0,
                "active_periods": [],
            }
            resp = client.get("/api/temporal/entity/p-1?limit=50")
            assert resp.status_code == 200

    def test_limit_too_high(self, client: TestClient):
        resp = client.get("/api/temporal/entity/p-1?limit=501")
        assert resp.status_code == 422


class TestInvestigationSnapshotsLimit:
    """GET /api/investigations/{id}/snapshots now accepts a limit parameter."""

    def test_limit_too_high(self, client: TestClient):
        resp = client.get("/api/investigations/inv-1/snapshots?limit=501")
        assert resp.status_code == 422

    def test_limit_zero(self, client: TestClient):
        resp = client.get("/api/investigations/inv-1/snapshots?limit=0")
        assert resp.status_code == 422
