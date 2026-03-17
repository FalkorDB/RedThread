"""Temporal graph analysis — track how the network evolves over time."""

from __future__ import annotations

from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)


def get_graph_at_time(
    client: FalkorDBClient,
    point_in_time: str,
    entity_id: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return the subgraph that was 'active' at a given point in time.

    A relationship is active at time T if:
      valid_from <= T AND (valid_to IS NULL OR valid_to >= T)

    For nodes, we include any node connected by at least one active relationship.
    """
    id_match = "{id: $eid}" if entity_id else ""

    query = (
        f"MATCH (a {id_match})-[r]->(b) "
        f"WHERE r.valid_from IS NOT NULL AND r.valid_from <= $pit "
        f"AND (r.valid_to IS NULL OR r.valid_to >= $pit) "
        f"WITH a, r, b, labels(a) AS a_lbls, labels(b) AS b_lbls "
        f"RETURN a, a_lbls, type(r) AS rel_type, properties(r) AS rprops, b, b_lbls "
        f"LIMIT $limit"
    )
    params: dict[str, Any] = {"pit": point_in_time, "limit": limit}
    if entity_id:
        params["eid"] = entity_id

    result = client.ro_query(query, params=params)

    nodes_map: dict[str, dict] = {}
    edges: list[dict] = []

    for row in result.result_set:
        a_node, a_lbls, rel_type, rprops, b_node, b_lbls = row
        a_props = dict(a_node.properties)
        a_props["label"] = a_lbls[0] if a_lbls else "Unknown"
        b_props = dict(b_node.properties)
        b_props["label"] = b_lbls[0] if b_lbls else "Unknown"

        nodes_map[a_props["id"]] = a_props
        nodes_map[b_props["id"]] = b_props
        edges.append(
            {
                "source": a_props["id"],
                "target": b_props["id"],
                "rel_type": rel_type,
                "properties": dict(rprops) if rprops else {},
            }
        )

    return {
        "point_in_time": point_in_time,
        "nodes": list(nodes_map.values()),
        "edges": edges,
        "node_count": len(nodes_map),
        "edge_count": len(edges),
    }


def get_changes_between(
    client: FalkorDBClient,
    start_date: str,
    end_date: str,
    limit: int = 200,
) -> dict[str, Any]:
    """Find relationships that were created or ended between two dates.

    Returns:
      - appeared: relationships with valid_from in [start, end]
      - disappeared: relationships with valid_to in [start, end]
      - active_throughout: relationships active during entire period
    """
    # Relationships that appeared in the window
    appeared_q = (
        "MATCH (a)-[r]->(b) "
        "WHERE r.valid_from IS NOT NULL "
        "AND r.valid_from >= $start AND r.valid_from <= $end "
        "WITH a, r, b, labels(a) AS a_lbls, labels(b) AS b_lbls "
        "RETURN a.id, a.name, a_lbls, type(r), properties(r), b.id, b.name, b_lbls "
        "LIMIT $limit"
    )
    params: dict[str, Any] = {"start": start_date, "end": end_date, "limit": limit}
    appeared_res = client.ro_query(appeared_q, params=params)

    appeared = []
    for row in appeared_res.result_set:
        appeared.append(
            {
                "source_id": row[0],
                "source_name": row[1],
                "source_label": row[2][0] if row[2] else "Unknown",
                "rel_type": row[3],
                "properties": dict(row[4]) if row[4] else {},
                "target_id": row[5],
                "target_name": row[6],
                "target_label": row[7][0] if row[7] else "Unknown",
                "change_type": "appeared",
            }
        )

    # Relationships that disappeared in the window
    disappeared_q = (
        "MATCH (a)-[r]->(b) "
        "WHERE r.valid_to IS NOT NULL "
        "AND r.valid_to >= $start AND r.valid_to <= $end "
        "WITH a, r, b, labels(a) AS a_lbls, labels(b) AS b_lbls "
        "RETURN a.id, a.name, a_lbls, type(r), properties(r), b.id, b.name, b_lbls "
        "LIMIT $limit"
    )
    disappeared_res = client.ro_query(disappeared_q, params=params)

    disappeared = []
    for row in disappeared_res.result_set:
        disappeared.append(
            {
                "source_id": row[0],
                "source_name": row[1],
                "source_label": row[2][0] if row[2] else "Unknown",
                "rel_type": row[3],
                "properties": dict(row[4]) if row[4] else {},
                "target_id": row[5],
                "target_name": row[6],
                "target_label": row[7][0] if row[7] else "Unknown",
                "change_type": "disappeared",
            }
        )

    logger.info(
        "temporal_changes",
        start=start_date,
        end=end_date,
        appeared=len(appeared),
        disappeared=len(disappeared),
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "appeared": appeared,
        "disappeared": disappeared,
        "total_changes": len(appeared) + len(disappeared),
    }


def get_relationship_timeline(
    client: FalkorDBClient,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Get all dated relationships ordered chronologically.

    Returns a flat timeline of events — when relationships formed and ended.
    """
    query = (
        "MATCH (a)-[r]->(b) "
        "WHERE r.valid_from IS NOT NULL "
        "WITH a, r, b, labels(a) AS a_lbls, labels(b) AS b_lbls "
        "RETURN a.id, a.name, a_lbls, type(r) AS rel_type, "
        "  r.valid_from AS vf, r.valid_to AS vt, "
        "  properties(r) AS rprops, b.id, b.name, b_lbls "
        "ORDER BY r.valid_from "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})

    timeline: list[dict[str, Any]] = []
    for row in result.result_set:
        entry = {
            "source_id": row[0],
            "source_name": row[1],
            "source_label": row[2][0] if row[2] else "Unknown",
            "rel_type": row[3],
            "valid_from": row[4],
            "valid_to": row[5],
            "properties": dict(row[6]) if row[6] else {},
            "target_id": row[7],
            "target_name": row[8],
            "target_label": row[9][0] if row[9] else "Unknown",
        }
        timeline.append(entry)

    return timeline


def get_date_range(client: FalkorDBClient) -> dict[str, str | None]:
    """Get the earliest and latest dates in the graph."""
    query = (
        "MATCH ()-[r]->() "
        "WHERE r.valid_from IS NOT NULL "
        "RETURN min(r.valid_from) AS earliest, max(r.valid_from) AS latest"
    )
    result = client.ro_query(query)
    if result.result_set:
        row = result.result_set[0]
        return {"earliest": row[0], "latest": row[1]}
    return {"earliest": None, "latest": None}


def get_entity_temporal_profile(
    client: FalkorDBClient,
    entity_id: str,
) -> dict[str, Any]:
    """Get a temporal profile for an entity — when relationships formed/ended."""
    query = (
        "MATCH (e {id: $eid})-[r]-(other) "
        "WHERE r.valid_from IS NOT NULL "
        "WITH r, other, labels(other) AS o_lbls, "
        "  CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END AS direction "
        "RETURN type(r) AS rel_type, direction, "
        "  r.valid_from AS vf, r.valid_to AS vt, "
        "  other.id AS other_id, other.name AS other_name, o_lbls "
        "ORDER BY r.valid_from"
    )
    result = client.ro_query(query, params={"eid": entity_id})

    events: list[dict[str, Any]] = []
    for row in result.result_set:
        events.append(
            {
                "rel_type": row[0],
                "direction": row[1],
                "valid_from": row[2],
                "valid_to": row[3],
                "other_id": row[4],
                "other_name": row[5],
                "other_label": row[6][0] if row[6] else "Unknown",
            }
        )

    # Compute activity windows
    active_periods: list[dict] = []
    for ev in events:
        active_periods.append(
            {
                "start": ev["valid_from"],
                "end": ev["valid_to"],
                "description": f"{ev['rel_type']} → {ev['other_name'] or ev['other_id']}",
            }
        )

    return {
        "entity_id": entity_id,
        "events": events,
        "total_events": len(events),
        "active_periods": active_periods,
    }
