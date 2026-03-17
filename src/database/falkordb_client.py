"""FalkorDB connection management with health checks."""

from __future__ import annotations

import time
from typing import Any

import structlog
from falkordb import FalkorDB, Graph

from src.config import settings

logger = structlog.get_logger(__name__)


class FalkorDBClient:
    """Manages FalkorDB connections and provides graph access."""

    def __init__(
        self,
        host: str = settings.falkordb_host,
        port: int = settings.falkordb_port,
        graph_name: str = settings.falkordb_graph_name,
    ) -> None:
        self._host = host
        self._port = port
        self._graph_name = graph_name
        self._db: FalkorDB | None = None
        self._graph: Graph | None = None

    def connect(self) -> None:
        """Establish connection to FalkorDB."""
        logger.info("connecting_to_falkordb", host=self._host, port=self._port)
        self._db = FalkorDB(host=self._host, port=self._port)
        self._graph = self._db.select_graph(self._graph_name)
        logger.info("falkordb_connected", graph=self._graph_name)

    @property
    def graph(self) -> Graph:
        """Get the active graph instance."""
        if self._graph is None:
            self.connect()
        assert self._graph is not None
        return self._graph

    def health_check(self) -> dict[str, Any]:
        """Check FalkorDB connectivity and return status."""
        try:
            start = time.monotonic()
            self.graph.query("RETURN 1")
            latency_ms = (time.monotonic() - start) * 1000
            return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
        except Exception as e:
            logger.error("falkordb_health_check_failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a Cypher query with optional parameters."""
        logger.debug("executing_query", query=cypher[:120], params=params)
        try:
            result = self.graph.query(cypher, params=params)
            return result
        except Exception as e:
            logger.error("query_failed", query=cypher[:120], error=str(e))
            raise

    def ro_query(self, cypher: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a read-only Cypher query."""
        logger.debug("executing_ro_query", query=cypher[:120], params=params)
        try:
            result = self.graph.ro_query(cypher, params=params)
            return result
        except Exception as e:
            logger.error("ro_query_failed", query=cypher[:120], error=str(e))
            raise

    def delete_graph(self) -> None:
        """Delete the entire graph — use with caution."""
        logger.warning("deleting_graph", graph=self._graph_name)
        try:
            self.graph.delete()
        except Exception:
            pass
        self._graph = self._db.select_graph(self._graph_name) if self._db else None

    def close(self) -> None:
        """Close the connection."""
        self._db = None
        self._graph = None
        logger.info("falkordb_connection_closed")


# Global client instance
db = FalkorDBClient()
