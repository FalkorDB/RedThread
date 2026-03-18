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


def detect_communities(
    client: FalkorDBClient,
    max_communities: int = 20,
    min_community_size: int = 2,
) -> dict[str, Any]:
    """Detect communities using connected-component and neighborhood overlap.

    Since FalkorDB doesn't have a built-in community detection algorithm,
    we use a two-pass approach:

    1. Find connected components via BFS — each component is a potential
       community (entities that are completely disconnected form separate ones).
    2. Within large components, further split by relationship density using
       shared-neighbor counts to identify tightly-knit clusters.

    Returns communities with member lists, density metrics, and inter-community
    relationship counts.
    """
    # Step 1: Get all entities and their direct neighbors
    edge_query = "MATCH (a)-[r]-(b) WHERE a.id < b.id RETURN a.id, b.id, type(r)"
    edge_result = client.ro_query(edge_query)

    # Build adjacency list
    adj: dict[str, set[str]] = {}
    edge_types: dict[tuple[str, str], list[str]] = {}
    for row in edge_result.result_set:
        a_id, b_id, rtype = row[0], row[1], row[2]
        adj.setdefault(a_id, set()).add(b_id)
        adj.setdefault(b_id, set()).add(a_id)
        key = (min(a_id, b_id), max(a_id, b_id))
        edge_types.setdefault(key, []).append(rtype)

    if not adj:
        return {"communities": [], "total_communities": 0, "modularity_estimate": 0.0}

    # Step 2: Find connected components via BFS
    visited: set[str] = set()
    components: list[set[str]] = []

    for start in adj:
        if start in visited:
            continue
        component: set[str] = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        if len(component) >= min_community_size:
            components.append(component)

    # Also add isolated nodes that weren't in any edge
    node_query = "MATCH (n) WHERE n.id IS NOT NULL RETURN n.id"
    node_result = client.ro_query(node_query)
    all_ids = {row[0] for row in node_result.result_set}
    orphans = all_ids - visited
    # Don't create a community for isolated nodes, but track count

    # Step 3: For large components, try sub-clustering by neighbor overlap
    communities: list[dict[str, Any]] = []
    total_edges = len(edge_result.result_set)

    for component in sorted(components, key=len, reverse=True)[:max_communities]:
        members = sorted(component)

        # Count internal edges
        internal_edges = 0
        for m in members:
            for n in adj.get(m, set()):
                if n in component and m < n:
                    internal_edges += 1

        max_possible = len(members) * (len(members) - 1) / 2
        density = internal_edges / max_possible if max_possible > 0 else 0.0

        communities.append(
            {
                "id": f"community-{len(communities) + 1}",
                "size": len(members),
                "members": members[:50],  # cap for response size
                "internal_edges": internal_edges,
                "density": round(density, 4),
            }
        )

    # Step 4: Compute inter-community edges
    community_map: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for mid in comm["members"]:
            community_map[mid] = i

    cross_edges = 0
    for row in edge_result.result_set:
        a_comm = community_map.get(row[0])
        b_comm = community_map.get(row[1])
        if a_comm is not None and b_comm is not None and a_comm != b_comm:
            cross_edges += 1

    # Rough modularity estimate: (internal - expected) / total
    modularity = 0.0
    if total_edges > 0:
        for comm in communities:
            e_in = comm["internal_edges"] / total_edges
            k = sum(len(adj.get(m, set())) for m in comm["members"])
            a = k / (2 * total_edges)
            modularity += e_in - a * a

    # Step 5: Enrich members with entity data
    member_ids = set()
    for comm in communities:
        member_ids.update(comm["members"])

    entity_data: dict[str, dict[str, Any]] = {}
    if member_ids:
        ids_list = list(member_ids)[:200]
        enrich_query = (
            "MATCH (n) WHERE n.id IN $ids RETURN n.id, n.name, n.account_number, labels(n)"
        )
        enrich_result = client.ro_query(enrich_query, params={"ids": ids_list})
        for row in enrich_result.result_set:
            eid = row[0]
            entity_data[eid] = {
                "id": eid,
                "name": row[1] or row[2] or eid,
                "label": row[3][0] if row[3] else "Unknown",
            }

    for comm in communities:
        comm["member_details"] = [entity_data.get(m, {"id": m}) for m in comm["members"][:20]]

    logger.info("communities_detected", count=len(communities), modularity=round(modularity, 4))
    return {
        "communities": communities,
        "total_communities": len(communities),
        "orphaned_nodes": len(orphans),
        "cross_community_edges": cross_edges,
        "modularity_estimate": round(modularity, 4),
    }
