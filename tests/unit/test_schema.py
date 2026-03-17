"""Unit tests for graph schema setup and statistics."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestSetupSchema:
    """Test schema/index creation."""

    def test_creates_indexes(self, clean_graph):
        """setup_schema creates indexes without errors on a fresh graph."""
        from src.database.schema import setup_schema

        # Should succeed even on a fresh graph
        setup_schema(clean_graph)

    def test_idempotent_second_call(self, clean_graph):
        """Second call hits the 'already indexed' path without raising."""
        from src.database.schema import setup_schema

        setup_schema(clean_graph)
        # Second call — indexes already exist — hits lines 34-36
        setup_schema(clean_graph)

    def test_index_creation_failure_is_logged(self):
        """Non-'already indexed' errors are logged as warnings, not raised."""
        from src.database.schema import setup_schema

        mock_client = MagicMock()
        mock_client.query.side_effect = RuntimeError("disk full")

        # Should NOT raise — error is logged and swallowed
        setup_schema(mock_client)

    def test_mixed_success_and_failure(self):
        """Some indexes succeed, some fail — all are attempted."""
        from src.database.schema import NODE_INDEXES, setup_schema

        call_count = 0
        total_expected = sum(len(v) for v in NODE_INDEXES.items())

        def side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise RuntimeError("intermittent failure")

        mock_client = MagicMock()
        mock_client.query.side_effect = side_effect

        setup_schema(mock_client)
        assert call_count >= total_expected


class TestGetGraphStats:
    """Test graph statistics collection."""

    def test_stats_with_seeded_data(self, seeded_graph):
        from src.database.schema import get_graph_stats

        stats = get_graph_stats(seeded_graph)
        assert stats["Person"] >= 2
        assert stats["Organization"] >= 2
        assert stats["Account"] >= 3
        assert stats["total_relationships"] >= 10
        assert stats["total_nodes"] >= 8

    def test_stats_empty_graph(self, clean_graph):
        from src.database.schema import get_graph_stats

        stats = get_graph_stats(clean_graph)
        assert stats["total_nodes"] == 0
        assert stats["total_relationships"] == 0

    def test_stats_node_count_failure(self):
        """When a per-label count query fails, that label defaults to 0."""
        from src.database.schema import get_graph_stats

        mock_client = MagicMock()
        mock_client.ro_query.side_effect = RuntimeError("connection lost")

        stats = get_graph_stats(mock_client)
        assert stats["Person"] == 0
        assert stats["total_relationships"] == 0

    def test_stats_relationship_count_failure(self):
        """When relationship count fails but node counts succeed."""
        from src.database.schema import get_graph_stats

        result_mock = MagicMock()
        result_mock.result_set = [[5]]

        call_count = 0

        def side_effect(query, **_kwargs):
            nonlocal call_count
            call_count += 1
            # Last query is the relationship count
            if "()-[r]->()" in query:
                raise RuntimeError("timeout")
            return result_mock

        mock_client = MagicMock()
        mock_client.ro_query.side_effect = side_effect

        stats = get_graph_stats(mock_client)
        assert stats["Person"] == 5
        assert stats["total_relationships"] == 0
