"""Graph schema setup — indexes and constraints for FalkorDB."""

from __future__ import annotations

import structlog

from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)

# Node labels and their indexed properties
NODE_INDEXES: dict[str, list[str]] = {
    "Person": ["id", "name", "nationality"],
    "Organization": ["id", "name", "jurisdiction", "org_type"],
    "Account": ["id", "account_number", "institution"],
    "Property": ["id", "property_type"],
    "Event": ["id", "event_type", "date"],
    "Document": ["id", "doc_type", "date"],
    "Address": ["id", "country", "city"],
    "Investigation": ["id", "name", "status"],
}


def setup_schema(client: FalkorDBClient) -> None:
    """Create indexes for all node types in the graph."""
    logger.info("setting_up_graph_schema")

    for label, properties in NODE_INDEXES.items():
        for prop in properties:
            try:
                query = f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"
                client.query(query)
                logger.debug("index_created", label=label, property=prop)
            except Exception as e:
                if "already indexed" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug("index_exists", label=label, property=prop)
                else:
                    logger.warning(
                        "index_creation_failed", label=label, property=prop, error=str(e)
                    )

    logger.info("graph_schema_setup_complete")


def get_graph_stats(client: FalkorDBClient) -> dict:
    """Get basic graph statistics."""
    stats: dict = {}
    labels = [
        "Person",
        "Organization",
        "Account",
        "Property",
        "Event",
        "Document",
        "Address",
        "Investigation",
    ]
    for label in labels:
        try:
            result = client.ro_query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
            stats[label] = result.result_set[0][0] if result.result_set else 0
        except Exception:
            stats[label] = 0

    try:
        result = client.ro_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        stats["total_relationships"] = result.result_set[0][0] if result.result_set else 0
    except Exception:
        stats["total_relationships"] = 0

    stats["total_nodes"] = sum(v for k, v in stats.items() if k != "total_relationships")
    return stats
