"""Path finding algorithms — all paths, shortest path, money flow tracing."""

from __future__ import annotations

from typing import Any

import structlog

from src.config import settings
from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)


def find_all_paths(
    client: FalkorDBClient,
    source_id: str,
    target_id: str,
    max_depth: int | None = None,
    rel_types: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find all paths between two entities up to max_depth hops.

    This is the core "connect the dots" query — variable-length traversal
    that would require recursive CTEs in SQL.
    """
    depth = min(max_depth or settings.max_path_depth, settings.max_path_depth)

    if rel_types:
        rel_filter = ":" + "|".join(rel_types)
    else:
        rel_filter = ""

    query = (
        f"MATCH path = (a {{id: $src}})-[{rel_filter}*1..{depth}]-(b {{id: $tgt}}) "
        f"RETURN path "
        f"ORDER BY length(path) "
        f"LIMIT $limit"
    )
    result = client.ro_query(query, params={"src": source_id, "tgt": target_id, "limit": limit})

    paths = []
    for row in result.result_set:
        path = row[0]
        path_data = _extract_path(path)
        paths.append(path_data)

    logger.info("paths_found", source=source_id, target=target_id, count=len(paths))
    return paths


def find_shortest_path(
    client: FalkorDBClient,
    source_id: str,
    target_id: str,
    rel_types: list[str] | None = None,
) -> dict[str, Any] | None:
    """Find the shortest path between two entities."""
    if rel_types:
        rel_filter = ":" + "|".join(rel_types)
    else:
        rel_filter = ""

    # FalkorDB requires directed shortestPath
    query = (
        f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
        f"RETURN shortestPath((a)-[{rel_filter}*1..{settings.max_path_depth}]->(b)) AS path"
    )
    result = client.ro_query(query, params={"src": source_id, "tgt": target_id})

    if not result.result_set or result.result_set[0][0] is None:
        # Try reverse direction
        query_rev = (
            f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
            f"RETURN shortestPath((b)-[{rel_filter}*1..{settings.max_path_depth}]->(a)) AS path"
        )
        result = client.ro_query(query_rev, params={"src": source_id, "tgt": target_id})
        if not result.result_set or result.result_set[0][0] is None:
            return None

    path = result.result_set[0][0]
    return _extract_path(path)


def trace_money_flow(
    client: FalkorDBClient,
    source_id: str,
    target_id: str | None = None,
    max_depth: int = 8,
    min_amount: float = 0.0,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Trace directed money flow through TRANSFERRED_TO relationships.

    This is a directed variable-length traversal with aggregation
    over path relationships — impossible in a single SQL query.
    """
    depth = min(max_depth, settings.max_path_depth)

    if target_id:
        query = (
            "MATCH path = (src:Account {id: $src})-[:TRANSFERRED_TO*1.."
            + str(depth)
            + "]->(dst:Account {id: $tgt}) "
            "WITH path, relationships(path) AS rels "
            "WITH path, "
            "  reduce(total = 0.0, r IN rels | total + coalesce(r.amount, 0)) AS total_flow, "
            "  reduce(mn = 999999999.0, r IN rels | "
            "    CASE WHEN coalesce(r.amount, 0) < mn THEN coalesce(r.amount, 0) ELSE mn END"
            "  ) AS min_transfer "
            "WHERE min_transfer >= $min_amount "
            "RETURN path, total_flow, min_transfer "
            "ORDER BY length(path) "
            "LIMIT $limit"
        )
        params: dict[str, Any] = {
            "src": source_id,
            "tgt": target_id,
            "min_amount": min_amount,
            "limit": limit,
        }
    else:
        # Find all downstream recipients from a source
        query = (
            "MATCH path = (src:Account {id: $src})-[:TRANSFERRED_TO*1.."
            + str(depth)
            + "]->(dst:Account) "
            "WITH path, dst, relationships(path) AS rels "
            "WITH path, dst, "
            "  reduce(total = 0.0, r IN rels | total + coalesce(r.amount, 0)) AS total_flow "
            "RETURN path, total_flow "
            "ORDER BY total_flow DESC "
            "LIMIT $limit"
        )
        params = {"src": source_id, "min_amount": min_amount, "limit": limit}

    result = client.ro_query(query, params=params)

    flows: list[dict[str, Any]] = []
    for row in result.result_set:
        path_data = _extract_path(row[0])
        path_data["total_flow"] = row[1]
        if len(row) > 2:
            path_data["min_transfer"] = row[2]
        flows.append(path_data)

    logger.info("money_flow_traced", source=source_id, flows_found=len(flows))
    return flows


def find_entity_reach(
    client: FalkorDBClient,
    entity_id: str,
    max_depth: int = 3,
    limit: int = 50,
) -> dict[str, Any]:
    """Find all entities reachable within N hops — the 'blast radius' of an entity.

    Returns entities grouped by hop distance.
    """
    depth = min(max_depth, settings.max_path_depth)
    query = (
        "MATCH (center {id: $id}) "
        "MATCH path = (center)-[*1.." + str(depth) + "]-(reached) "
        "WHERE reached.id <> $id "
        "WITH DISTINCT reached, length(path) AS dist, labels(reached) AS lbls "
        "RETURN reached, min(dist) AS min_dist, lbls "
        "ORDER BY min_dist "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"id": entity_id, "limit": limit})

    by_distance: dict[int, list[dict]] = {}
    for row in result.result_set:
        node = row[0]
        dist = row[1]
        lbls = row[2]
        props = dict(node.properties)
        props["label"] = lbls[0] if lbls else "Unknown"
        props["distance"] = dist
        by_distance.setdefault(dist, []).append(props)

    return {
        "center_id": entity_id,
        "max_depth": depth,
        "by_distance": by_distance,
        "total_reached": sum(len(v) for v in by_distance.values()),
    }


def _extract_path(path: Any) -> dict[str, Any]:
    """Extract nodes and edges from a FalkorDB path object."""
    nodes = []
    edges = []

    path_nodes = path.nodes()
    path_edges = path.edges()

    for node in path_nodes:
        props = dict(node.properties)
        labels = node.labels
        props["label"] = labels[0] if labels else "Unknown"
        nodes.append(props)

    for edge in path_edges:
        edges.append(
            {
                "source": edge.src_node,
                "target": edge.dest_node,
                "rel_type": edge.relation,
                "properties": dict(edge.properties) if edge.properties else {},
            }
        )

    return {"nodes": nodes, "edges": edges, "length": len(path_edges)}
