"""Unit tests for graph analytics — centrality, bridges, shared connections, timeline."""

from __future__ import annotations


class TestDegreeCentrality:
    """Test degree centrality computation."""

    def test_most_connected_entity(self, seeded_graph):
        from src.graph.analytics import degree_centrality

        results = degree_centrality(seeded_graph, limit=5)
        assert len(results) > 0
        # All results should have a degree field
        for r in results:
            assert "degree" in r
            assert r["degree"] > 0

    def test_centrality_ordered_desc(self, seeded_graph):
        from src.graph.analytics import degree_centrality

        results = degree_centrality(seeded_graph, limit=10)
        if len(results) > 1:
            degrees = [r["degree"] for r in results]
            assert degrees == sorted(degrees, reverse=True)

    def test_centrality_with_label_filter(self, seeded_graph):
        from src.graph.analytics import degree_centrality

        results = degree_centrality(seeded_graph, label="Account", limit=10)
        for r in results:
            assert r["label"] == "Account"

    def test_centrality_respects_limit(self, seeded_graph):
        from src.graph.analytics import degree_centrality

        results = degree_centrality(seeded_graph, limit=2)
        assert len(results) <= 2

    def test_centrality_empty_graph(self, clean_graph):
        from src.graph.analytics import degree_centrality

        results = degree_centrality(clean_graph, limit=5)
        assert results == []


class TestBetweennessProxy:
    """Test bridge entity detection."""

    def test_bridge_entities_found(self, seeded_graph):
        from src.graph.analytics import betweenness_proxy

        results = betweenness_proxy(seeded_graph, limit=5)
        assert len(results) > 0
        for r in results:
            assert "bridge_score" in r
            assert "type_diversity" in r
            assert "neighbor_count" in r

    def test_bridge_score_ordered_desc(self, seeded_graph):
        from src.graph.analytics import betweenness_proxy

        results = betweenness_proxy(seeded_graph, limit=10)
        if len(results) > 1:
            scores = [r["bridge_score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_bridge_with_label_filter(self, seeded_graph):
        from src.graph.analytics import betweenness_proxy

        results = betweenness_proxy(seeded_graph, label="Person", limit=10)
        for r in results:
            assert r["label"] == "Person"

    def test_bridge_empty_graph(self, clean_graph):
        from src.graph.analytics import betweenness_proxy

        results = betweenness_proxy(clean_graph, limit=5)
        assert results == []


class TestSharedConnections:
    """Test shared connection discovery between two entities."""

    def test_shared_connections_between_related_entities(self, seeded_graph):
        from src.graph.analytics import shared_connections

        # test-p1 and test-p2 both connect through organizations/accounts
        results = shared_connections(seeded_graph, "test-p1", "test-p2", max_depth=2)
        assert isinstance(results, list)
        # They share connections through Shell Corp and/or Real Corp
        if results:
            for r in results:
                assert "label" in r
                assert "id" in r

    def test_shared_connections_nonexistent_entity(self, seeded_graph):
        from src.graph.analytics import shared_connections

        results = shared_connections(seeded_graph, "test-p1", "nonexistent", max_depth=2)
        assert results == []

    def test_shared_connections_same_entity(self, seeded_graph):
        from src.graph.analytics import shared_connections

        results = shared_connections(seeded_graph, "test-p1", "test-p1", max_depth=2)
        # Same entity should return neighbors as "shared"
        assert isinstance(results, list)

    def test_shared_connections_empty_graph(self, clean_graph):
        from src.graph.analytics import shared_connections

        results = shared_connections(clean_graph, "a", "b", max_depth=2)
        assert results == []


class TestEntityTimeline:
    """Test chronological entity timeline retrieval."""

    def test_timeline_returns_dated_events(self, seeded_graph):
        from src.graph.analytics import get_entity_timeline

        # test-a1 has TRANSFERRED_TO with dates
        events = get_entity_timeline(seeded_graph, "test-a1")
        assert isinstance(events, list)
        if events:
            for ev in events:
                assert "rel_type" in ev
                assert "date" in ev

    def test_timeline_ordered_chronologically(self, seeded_graph):
        from src.graph.analytics import get_entity_timeline

        events = get_entity_timeline(seeded_graph, "test-a1")
        if len(events) > 1:
            dates = [e["date"] for e in events if e["date"]]
            assert dates == sorted(dates)

    def test_timeline_nonexistent_entity(self, seeded_graph):
        from src.graph.analytics import get_entity_timeline

        events = get_entity_timeline(seeded_graph, "nonexistent")
        assert events == []

    def test_timeline_respects_limit(self, seeded_graph):
        from src.graph.analytics import get_entity_timeline

        events = get_entity_timeline(seeded_graph, "test-a1", limit=1)
        assert len(events) <= 1


class TestGraphSummary:
    """Test graph summary statistics."""

    def test_summary_has_expected_keys(self, seeded_graph):
        from src.graph.analytics import graph_summary

        stats = graph_summary(seeded_graph)
        assert "total_nodes" in stats
        assert "total_relationships" in stats
        assert "relationship_types" in stats
        assert "Person" in stats
        assert "Organization" in stats
        assert "Account" in stats

    def test_summary_counts_entities(self, seeded_graph):
        from src.graph.analytics import graph_summary

        stats = graph_summary(seeded_graph)
        assert stats["Person"] >= 2
        assert stats["Organization"] >= 2
        assert stats["Account"] >= 3
        assert stats["total_nodes"] >= 7

    def test_summary_counts_relationships(self, seeded_graph):
        from src.graph.analytics import graph_summary

        stats = graph_summary(seeded_graph)
        assert stats["total_relationships"] >= 5
        assert isinstance(stats["relationship_types"], dict)

    def test_summary_empty_graph(self, clean_graph):
        from src.graph.analytics import graph_summary

        stats = graph_summary(clean_graph)
        assert stats["total_nodes"] == 0
        assert stats["total_relationships"] == 0
