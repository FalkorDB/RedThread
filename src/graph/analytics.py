"""Graph analytics — centrality, clustering, statistics."""

from __future__ import annotations

from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)


def degree_centrality(
    client: FalkorDBClient,
    label: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Compute degree centrality — entities with the most connections.

    High degree centrality often indicates key players, hubs, or
    entities worth investigating more deeply.
    """
    if label:
        from src.graph.cypher_utils import validate_label

        validate_label(label)
    label_filter = f":{label}" if label else ""
    query = (
        f"MATCH (n{label_filter})-[r]-() "
        f"WITH n, labels(n) AS lbls, count(r) AS degree "
        f"RETURN n, lbls, degree "
        f"ORDER BY degree DESC "
        f"LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})

    entities = []
    for row in result.result_set:
        props = dict(row[0].properties)
        props["label"] = row[1][0] if row[1] else "Unknown"
        props["degree"] = row[2]
        entities.append(props)
    return entities


def betweenness_proxy(
    client: FalkorDBClient,
    label: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Approximate betweenness centrality — entities that bridge groups.

    True betweenness requires all-pairs shortest paths, which is expensive.
    This proxy finds entities connected to many different entity types
    or entities in different clusters (by jurisdiction/nationality).
    """
    if label:
        from src.graph.cypher_utils import validate_label

        validate_label(label)
    label_filter = f":{label}" if label else ""
    query = (
        f"MATCH (n{label_filter})-[r]-(m) "
        f"WITH n, labels(n) AS lbls, "
        f"  count(DISTINCT labels(m)) AS type_diversity, "
        f"  count(DISTINCT m) AS neighbor_count "
        f"RETURN n, lbls, type_diversity, neighbor_count, "
        f"  type_diversity * neighbor_count AS bridge_score "
        f"ORDER BY bridge_score DESC "
        f"LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})

    entities = []
    for row in result.result_set:
        props = dict(row[0].properties)
        props["label"] = row[1][0] if row[1] else "Unknown"
        props["type_diversity"] = row[2]
        props["neighbor_count"] = row[3]
        props["bridge_score"] = row[4]
        entities.append(props)
    return entities


def shared_connections(
    client: FalkorDBClient,
    entity_id_1: str,
    entity_id_2: str,
    max_depth: int = 2,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find shared connections between two entities.

    Entities that both targets connect to within N hops are
    potential co-conspirators, shared resources, or common infrastructure.
    """
    depth = min(max_depth, 4)
    query = (
        "MATCH (a {id: $id1})-[*1.."
        + str(depth)
        + "]-(shared)-[*1.."
        + str(depth)
        + "]-(b {id: $id2}) "
        "WHERE shared.id <> $id1 AND shared.id <> $id2 "
        "WITH DISTINCT shared, labels(shared) AS lbls "
        "RETURN shared, lbls "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"id1": entity_id_1, "id2": entity_id_2, "limit": limit})

    entities = []
    for row in result.result_set:
        props = dict(row[0].properties)
        props["label"] = row[1][0] if row[1] else "Unknown"
        entities.append(props)
    return entities


def get_entity_timeline(
    client: FalkorDBClient,
    entity_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get a chronological timeline of all dated relationships for an entity."""
    query = (
        "MATCH (e {id: $id})-[r]-(other) "
        "WHERE r.date IS NOT NULL "
        "WITH r, other, labels(other) AS lbls "
        "RETURN type(r) AS rel_type, r.date AS date, "
        "  other.id AS other_id, other.name AS other_name, lbls, "
        "  properties(r) AS props "
        "ORDER BY r.date "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"id": entity_id, "limit": limit})

    events = []
    for row in result.result_set:
        events.append(
            {
                "rel_type": row[0],
                "date": row[1],
                "other_id": row[2],
                "other_name": row[3],
                "other_label": row[4][0] if row[4] else "Unknown",
                "properties": row[5] if row[5] else {},
            }
        )
    return events


def graph_summary(client: FalkorDBClient) -> dict[str, Any]:
    """Get comprehensive graph statistics."""
    from src.database.schema import get_graph_stats

    stats = get_graph_stats(client)

    # Get relationship type counts
    try:
        rel_query = (
            "MATCH ()-[r]->() "
            "WITH type(r) AS rel_type, count(r) AS cnt "
            "RETURN rel_type, cnt ORDER BY cnt DESC"
        )
        rel_result = client.ro_query(rel_query)
        rel_counts = {row[0]: row[1] for row in rel_result.result_set}
    except Exception:
        rel_counts = {}

    stats["relationship_types"] = rel_counts
    return stats
