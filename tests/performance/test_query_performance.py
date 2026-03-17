"""Performance regression tests for critical graph queries.

These tests verify that key queries execute within acceptable time bounds
on the seeded demo dataset. They are integration tests that require a
running FalkorDB instance.
"""

from __future__ import annotations

import time

import pytest

from src.graph import analytics, pathfinding, patterns, risk_scoring


@pytest.fixture()
def _require_seeded_data(seeded_graph):
    """Ensure the graph has demo data for meaningful benchmark results."""
    return seeded_graph


def _time_ms(fn, *args, **kwargs) -> tuple[object, float]:
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, (time.perf_counter() - start) * 1000


@pytest.mark.usefixtures("_require_seeded_data")
class TestPatternPerformance:
    """Pattern detection queries must complete quickly on small graphs."""

    def test_circular_flows_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            patterns.detect_circular_flows,
            falkordb_client,
            min_amount=0,
            limit=20,
        )
        assert ms < 500, f"detect_circular_flows took {ms:.1f}ms (limit 500ms)"

    def test_shell_company_chains_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            patterns.detect_shell_company_chains,
            falkordb_client,
            min_depth=2,
            limit=20,
        )
        assert ms < 500, f"detect_shell_company_chains took {ms:.1f}ms (limit 500ms)"

    def test_structuring_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            patterns.detect_structuring,
            falkordb_client,
            threshold=10000,
            min_count=2,
            limit=20,
        )
        assert ms < 500, f"detect_structuring took {ms:.1f}ms (limit 500ms)"

    def test_rapid_passthrough_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            patterns.detect_rapid_passthrough,
            falkordb_client,
            min_amount=0,
            limit=20,
        )
        assert ms < 500, f"detect_rapid_passthrough took {ms:.1f}ms (limit 500ms)"


@pytest.mark.usefixtures("_require_seeded_data")
class TestPathfindingPerformance:
    """Pathfinding queries must complete quickly on small graphs."""

    def test_find_all_paths_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            pathfinding.find_all_paths,
            falkordb_client,
            source_id="test-p1",
            target_id="test-p2",
            max_depth=6,
            limit=20,
        )
        assert ms < 500, f"find_all_paths took {ms:.1f}ms (limit 500ms)"

    def test_find_shortest_path_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            pathfinding.find_shortest_path,
            falkordb_client,
            source_id="test-p1",
            target_id="test-p2",
        )
        assert ms < 500, f"find_shortest_path took {ms:.1f}ms (limit 500ms)"

    def test_trace_money_flow_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            pathfinding.trace_money_flow,
            falkordb_client,
            source_id="test-a1",
            min_amount=0,
            limit=20,
        )
        assert ms < 500, f"trace_money_flow took {ms:.1f}ms (limit 500ms)"

    def test_entity_reach_under_500ms(self, falkordb_client):
        _, ms = _time_ms(
            pathfinding.find_entity_reach,
            falkordb_client,
            entity_id="test-p1",
            max_depth=3,
            limit=50,
        )
        assert ms < 500, f"find_entity_reach took {ms:.1f}ms (limit 500ms)"


@pytest.mark.usefixtures("_require_seeded_data")
class TestAnalyticsPerformance:
    """Analytics queries must complete quickly on small graphs."""

    def test_degree_centrality_under_500ms(self, falkordb_client):
        _, ms = _time_ms(analytics.degree_centrality, falkordb_client, limit=20)
        assert ms < 500, f"degree_centrality took {ms:.1f}ms (limit 500ms)"

    def test_betweenness_proxy_under_500ms(self, falkordb_client):
        _, ms = _time_ms(analytics.betweenness_proxy, falkordb_client, limit=20)
        assert ms < 500, f"betweenness_proxy took {ms:.1f}ms (limit 500ms)"

    def test_graph_summary_under_500ms(self, falkordb_client):
        _, ms = _time_ms(analytics.graph_summary, falkordb_client)
        assert ms < 500, f"graph_summary took {ms:.1f}ms (limit 500ms)"


@pytest.mark.usefixtures("_require_seeded_data")
class TestRiskPerformance:
    """Risk scoring queries must complete quickly on small graphs."""

    def test_compute_entity_risk_under_500ms(self, falkordb_client):
        _, ms = _time_ms(risk_scoring.compute_entity_risk, falkordb_client, entity_id="test-p1")
        assert ms < 500, f"compute_entity_risk took {ms:.1f}ms (limit 500ms)"

    def test_compute_network_risk_under_1000ms(self, falkordb_client):
        _, ms = _time_ms(
            risk_scoring.compute_network_risk,
            falkordb_client,
            entity_ids=["test-p1", "test-p2"],
        )
        assert ms < 1000, f"compute_network_risk took {ms:.1f}ms (limit 1000ms)"

    def test_highest_risk_under_500ms(self, falkordb_client):
        _, ms = _time_ms(risk_scoring.get_highest_risk_entities, falkordb_client, limit=10)
        assert ms < 500, f"get_highest_risk_entities took {ms:.1f}ms (limit 500ms)"
