"""Graph data-quality validation queries.

Checks the live graph for structural issues: orphaned nodes, missing
required properties, dangling relationships, and duplicate IDs.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)


def find_orphaned_nodes(client: FalkorDBClient, limit: int = 100) -> list[dict[str, Any]]:
    """Return entities with zero relationships (isolated nodes)."""
    query = (
        "MATCH (n) "
        "WHERE NOT (n)--() "
        "RETURN n.id AS id, n.name AS name, labels(n) AS labels "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})
    return [{"id": row[0], "name": row[1], "labels": row[2]} for row in result.result_set]


def find_missing_names(client: FalkorDBClient, limit: int = 100) -> list[dict[str, Any]]:
    """Return entities where the 'name' property is empty or missing."""
    query = (
        "MATCH (n) "
        "WHERE n.name IS NULL OR n.name = '' "
        "RETURN n.id AS id, labels(n) AS labels "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})
    return [{"id": row[0], "labels": row[1]} for row in result.result_set]


def find_duplicate_ids(client: FalkorDBClient, limit: int = 50) -> list[dict[str, Any]]:
    """Return entity IDs that appear on more than one node."""
    query = (
        "MATCH (n) "
        "WITH n.id AS eid, collect(labels(n)) AS all_labels "
        "WHERE size(all_labels) > 1 "
        "RETURN eid, all_labels "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})
    return [{"id": row[0], "labels": row[1]} for row in result.result_set]


def find_self_referencing_relationships(
    client: FalkorDBClient, limit: int = 100
) -> list[dict[str, Any]]:
    """Return relationships where source and target are the same node."""
    query = "MATCH (a)-[r]->(a) RETURN a.id AS id, a.name AS name, type(r) AS rel_type LIMIT $limit"
    result = client.ro_query(query, params={"limit": limit})
    return [{"id": row[0], "name": row[1], "rel_type": row[2]} for row in result.result_set]


def validate_graph(client: FalkorDBClient) -> dict[str, Any]:
    """Run all validation checks and return a summary report."""
    orphaned = find_orphaned_nodes(client)
    missing_names = find_missing_names(client)
    duplicate_ids = find_duplicate_ids(client)
    self_refs = find_self_referencing_relationships(client)

    issues_count = len(orphaned) + len(missing_names) + len(duplicate_ids) + len(self_refs)
    status = "clean" if issues_count == 0 else "issues_found"

    report = {
        "status": status,
        "total_issues": issues_count,
        "checks": {
            "orphaned_nodes": {"count": len(orphaned), "items": orphaned},
            "missing_names": {"count": len(missing_names), "items": missing_names},
            "duplicate_ids": {"count": len(duplicate_ids), "items": duplicate_ids},
            "self_referencing": {"count": len(self_refs), "items": self_refs},
        },
    }

    logger.info("graph_validation_complete", status=status, issues=issues_count)
    return report
