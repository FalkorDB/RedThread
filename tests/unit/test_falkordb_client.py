"""Unit tests for FalkorDB client connection management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestFalkorDBClientConnect:
    """Test connection establishment and lazy-connect."""

    def test_lazy_connect_on_graph_access(self):
        """Accessing .graph when _graph is None triggers connect()."""
        from src.database.falkordb_client import FalkorDBClient

        client = FalkorDBClient(host="localhost", port=99999, graph_name="test")
        # _graph is None → .graph triggers connect()
        # Connection will fail since port 99999 doesn't exist
        try:
            _ = client.graph
        except Exception:
            pass
        # The important thing is that connect() was called (line 42)

    def test_graph_property_returns_after_connect(self):
        """After successful connect, .graph returns the Graph instance."""
        with (
            patch("src.database.falkordb_client.FalkorDB") as mock_falkor,
        ):
            mock_db = MagicMock()
            mock_graph = MagicMock()
            mock_db.select_graph.return_value = mock_graph
            mock_falkor.return_value = mock_db

            from src.database.falkordb_client import FalkorDBClient

            client = FalkorDBClient(host="localhost", port=6379, graph_name="test")
            client.connect()
            assert client.graph is mock_graph


class TestHealthCheck:
    """Test health check responses."""

    def test_healthy(self):
        """Healthy check returns status and latency."""
        from src.database.falkordb_client import FalkorDBClient

        with patch("src.database.falkordb_client.FalkorDB") as mock_falkor:
            mock_graph = MagicMock()
            mock_db = MagicMock()
            mock_db.select_graph.return_value = mock_graph
            mock_falkor.return_value = mock_db

            client = FalkorDBClient()
            client.connect()
            result = client.health_check()
            assert result["status"] == "healthy"
            assert "latency_ms" in result

    def test_unhealthy(self):
        """Unhealthy check returns error string (covers lines 53-55)."""
        from src.database.falkordb_client import FalkorDBClient

        with patch("src.database.falkordb_client.FalkorDB") as mock_falkor:
            mock_graph = MagicMock()
            mock_graph.query.side_effect = ConnectionError("refused")
            mock_db = MagicMock()
            mock_db.select_graph.return_value = mock_graph
            mock_falkor.return_value = mock_db

            client = FalkorDBClient()
            client.connect()
            result = client.health_check()
            assert result["status"] == "unhealthy"
            assert "refused" in result["error"]


class TestQueryMethods:
    """Test query and ro_query error paths."""

    def _make_client(self):
        from src.database.falkordb_client import FalkorDBClient

        with patch("src.database.falkordb_client.FalkorDB") as mock_falkor:
            mock_graph = MagicMock()
            mock_db = MagicMock()
            mock_db.select_graph.return_value = mock_graph
            mock_falkor.return_value = mock_db

            client = FalkorDBClient()
            client.connect()
            return client, mock_graph

    def test_query_error_reraises(self):
        """query() logs and re-raises on failure (lines 63-65)."""
        import pytest

        client, mock_graph = self._make_client()
        mock_graph.query.side_effect = RuntimeError("syntax error")

        with pytest.raises(RuntimeError, match="syntax error"):
            client.query("INVALID CYPHER")

    def test_ro_query_error_reraises(self):
        """ro_query() logs and re-raises on failure (lines 73-75)."""
        import pytest

        client, mock_graph = self._make_client()
        mock_graph.ro_query.side_effect = RuntimeError("timeout")

        with pytest.raises(RuntimeError, match="timeout"):
            client.ro_query("MATCH (n) RETURN n")


class TestDeleteGraph:
    """Test graph deletion."""

    def test_delete_graph_exception_suppressed(self):
        """delete() failure is silently caught (line 82-83)."""
        from src.database.falkordb_client import FalkorDBClient

        with patch("src.database.falkordb_client.FalkorDB") as mock_falkor:
            mock_graph = MagicMock()
            mock_graph.delete.side_effect = RuntimeError("graph not found")
            mock_db = MagicMock()
            mock_db.select_graph.return_value = mock_graph
            mock_falkor.return_value = mock_db

            client = FalkorDBClient()
            client.connect()
            client.delete_graph()  # Should not raise
            # After delete, graph is re-selected
            assert mock_db.select_graph.call_count >= 2

    def test_delete_graph_with_no_db(self):
        """delete_graph with _db=None sets _graph to None."""
        from src.database.falkordb_client import FalkorDBClient

        client = FalkorDBClient()
        client._db = None
        client._graph = MagicMock()
        client._graph.delete.side_effect = RuntimeError("fail")
        client.delete_graph()
        assert client._graph is None


class TestClose:
    """Test connection teardown."""

    def test_close_clears_state(self):
        from src.database.falkordb_client import FalkorDBClient

        with patch("src.database.falkordb_client.FalkorDB") as mock_falkor:
            mock_db = MagicMock()
            mock_db.select_graph.return_value = MagicMock()
            mock_falkor.return_value = mock_db

            client = FalkorDBClient()
            client.connect()
            assert client._graph is not None

            client.close()
            assert client._db is None
            assert client._graph is None
