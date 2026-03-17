"""Integration tests for the analysis API endpoints.

These tests exercise /api/analysis/* via the FastAPI TestClient with a
seeded graph (8 entities, 10 relationships including circular money flows).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client(seeded_graph) -> TestClient:
    """Return a TestClient backed by a seeded graph."""
    from src.main import app

    return TestClient(app)


# ── Path-finding ────────────────────────────────────────────────────


class TestPaths:
    """Tests for /api/analysis/paths."""

    def test_find_paths_between_accounts(self, client: TestClient):
        """a1→a2→a3→a1 cycle means multiple paths exist."""
        resp = client.get("/api/analysis/paths", params={"source": "test-a1", "target": "test-a2"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "test-a1"
        assert data["target"] == "test-a2"
        assert isinstance(data["paths"], list)
        assert data["count"] >= 1

    def test_find_paths_no_connection(self, client: TestClient):
        resp = client.get(
            "/api/analysis/paths", params={"source": "test-addr1", "target": "test-p2"}
        )
        assert resp.status_code == 200

    def test_find_paths_with_rel_type_filter(self, client: TestClient):
        resp = client.get(
            "/api/analysis/paths",
            params={"source": "test-a1", "target": "test-a2", "rel_types": "TRANSFERRED_TO"},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_find_paths_with_limit(self, client: TestClient):
        resp = client.get(
            "/api/analysis/paths",
            params={"source": "test-a1", "target": "test-a2", "limit": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] <= 1

    def test_find_paths_requires_source_target(self, client: TestClient):
        resp = client.get("/api/analysis/paths")
        assert resp.status_code == 422


class TestShortestPath:
    """Tests for /api/analysis/shortest-path."""

    def test_shortest_path_found(self, client: TestClient):
        resp = client.get(
            "/api/analysis/shortest-path", params={"source": "test-a1", "target": "test-a2"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["path"] is not None

    def test_shortest_path_not_found(self, client: TestClient):
        resp = client.get(
            "/api/analysis/shortest-path", params={"source": "test-addr1", "target": "nonexist"}
        )
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_shortest_path_with_rel_filter(self, client: TestClient):
        resp = client.get(
            "/api/analysis/shortest-path",
            params={"source": "test-a1", "target": "test-a2", "rel_types": "TRANSFERRED_TO"},
        )
        assert resp.status_code == 200
        assert resp.json()["found"] is True


# ── Money flow ──────────────────────────────────────────────────────


class TestMoneyFlow:
    """Tests for /api/analysis/money-flow."""

    def test_trace_from_source(self, client: TestClient):
        resp = client.get("/api/analysis/money-flow", params={"source": "test-a1"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["flows"], list)
        assert data["count"] >= 1

    def test_trace_with_target(self, client: TestClient):
        resp = client.get(
            "/api/analysis/money-flow", params={"source": "test-a1", "target": "test-a3"}
        )
        assert resp.status_code == 200

    def test_trace_with_min_amount(self, client: TestClient):
        """Source-only branch doesn't filter by min_amount, just returns all flows."""
        resp = client.get(
            "/api/analysis/money-flow", params={"source": "test-a1", "min_amount": 100000}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["flows"], list)

    def test_trace_nonexistent_source(self, client: TestClient):
        resp = client.get("/api/analysis/money-flow", params={"source": "no-such-account"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ── Reach ───────────────────────────────────────────────────────────


class TestReach:
    """Tests for /api/analysis/reach."""

    def test_entity_reach(self, client: TestClient):
        resp = client.get("/api/analysis/reach", params={"entity_id": "test-p1"})
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data or "nodes" in data or isinstance(data, dict)

    def test_entity_reach_with_depth(self, client: TestClient):
        resp = client.get("/api/analysis/reach", params={"entity_id": "test-p1", "max_depth": 1})
        assert resp.status_code == 200

    def test_entity_reach_nonexistent(self, client: TestClient):
        resp = client.get("/api/analysis/reach", params={"entity_id": "no-such-entity"})
        assert resp.status_code == 200


# ── Patterns ────────────────────────────────────────────────────────


class TestPatterns:
    """Tests for /api/analysis/patterns/*."""

    def test_all_patterns(self, client: TestClient):
        resp = client.get("/api/analysis/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_circular_flows(self, client: TestClient):
        """Seeded graph has a1→a2→a3→a1 cycle."""
        resp = client.get("/api/analysis/patterns/circular-flows")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["patterns"], list)
        assert data["count"] >= 1

    def test_circular_flows_with_params(self, client: TestClient):
        resp = client.get(
            "/api/analysis/patterns/circular-flows",
            params={"min_length": 3, "max_length": 5, "min_amount": 0},
        )
        assert resp.status_code == 200

    def test_shell_companies(self, client: TestClient):
        resp = client.get("/api/analysis/patterns/shell-companies")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["patterns"], list)

    def test_structuring(self, client: TestClient):
        resp = client.get("/api/analysis/patterns/structuring")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["patterns"], list)

    def test_structuring_with_params(self, client: TestClient):
        resp = client.get(
            "/api/analysis/patterns/structuring",
            params={"threshold": 50000, "tolerance_pct": 10, "min_count": 2},
        )
        assert resp.status_code == 200

    def test_passthrough(self, client: TestClient):
        resp = client.get("/api/analysis/patterns/passthrough")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["patterns"], list)

    def test_hidden_connections(self, client: TestClient):
        resp = client.get(
            "/api/analysis/patterns/hidden-connections",
            params={"entity1": "test-p1", "entity2": "test-p2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["connections"], list)

    def test_hidden_connections_requires_both(self, client: TestClient):
        resp = client.get(
            "/api/analysis/patterns/hidden-connections", params={"entity1": "test-p1"}
        )
        assert resp.status_code == 422


# ── Risk scoring ────────────────────────────────────────────────────


class TestRisk:
    """Tests for /api/analysis/risk."""

    def test_compute_risk_for_entity(self, client: TestClient):
        resp = client.get("/api/analysis/risk/test-p1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_compute_risk_with_depth(self, client: TestClient):
        resp = client.get("/api/analysis/risk/test-p1", params={"depth": 2})
        assert resp.status_code == 200

    def test_compute_risk_nonexistent_entity(self, client: TestClient):
        resp = client.get("/api/analysis/risk/no-such-entity")
        assert resp.status_code == 200

    def test_highest_risk_entities(self, client: TestClient):
        resp = client.get("/api/analysis/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_highest_risk_with_limit(self, client: TestClient):
        resp = client.get("/api/analysis/risk", params={"limit": 3})
        assert resp.status_code == 200
        assert len(resp.json()) <= 3


# ── Analytics ───────────────────────────────────────────────────────


class TestAnalytics:
    """Tests for centrality, bridges, shared-connections, timeline, stats."""

    def test_centrality(self, client: TestClient):
        resp = client.get("/api/analysis/centrality")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_centrality_with_label(self, client: TestClient):
        resp = client.get("/api/analysis/centrality", params={"label": "Person"})
        assert resp.status_code == 200

    def test_centrality_with_limit(self, client: TestClient):
        resp = client.get("/api/analysis/centrality", params={"limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    def test_bridges(self, client: TestClient):
        resp = client.get("/api/analysis/bridges")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_bridges_with_label(self, client: TestClient):
        resp = client.get("/api/analysis/bridges", params={"label": "Organization"})
        assert resp.status_code == 200

    def test_shared_connections(self, client: TestClient):
        resp = client.get(
            "/api/analysis/shared-connections",
            params={"entity1": "test-p1", "entity2": "test-p2"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_shared_connections_requires_both(self, client: TestClient):
        resp = client.get("/api/analysis/shared-connections", params={"entity1": "test-p1"})
        assert resp.status_code == 422

    def test_timeline(self, client: TestClient):
        resp = client.get("/api/analysis/timeline/test-a1")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_timeline_with_limit(self, client: TestClient):
        resp = client.get("/api/analysis/timeline/test-a1", params={"limit": 5})
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    def test_timeline_nonexistent(self, client: TestClient):
        resp = client.get("/api/analysis/timeline/no-such-entity")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_graph_stats(self, client: TestClient):
        resp = client.get("/api/analysis/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Stats include per-label counts; seeded graph has Person, Organization, etc.
        assert data.get("Person", 0) > 0 or data.get("total_entities", 0) > 0
