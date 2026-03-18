"""Core Cypher queries for entity and relationship CRUD in FalkorDB."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient
from src.graph.cypher_utils import validate_label, validate_rel_type

logger = structlog.get_logger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())[:12]


def create_entity(client: FalkorDBClient, label: str, properties: dict[str, Any]) -> dict[str, Any]:
    """Create a node with the given label and properties."""
    validate_label(label)
    entity_id = properties.get("id") or _new_id()
    properties["id"] = entity_id
    properties["created_at"] = _now()
    properties["updated_at"] = _now()

    # Convert lists to JSON strings for storage
    for key, val in properties.items():
        if isinstance(val, list):
            properties[key] = json.dumps(val)

    # Remove empty string values to keep graph clean
    props = {k: v for k, v in properties.items() if v != "" and v is not None}

    set_clauses = ", ".join(f"n.{k} = ${k}" for k in props)
    query = f"CREATE (n:{label}) SET {set_clauses} RETURN n"
    client.query(query, params=props)

    logger.info("entity_created", label=label, id=entity_id)
    return {"id": entity_id, "label": label, **props}


def get_entity(client: FalkorDBClient, label: str, entity_id: str) -> dict[str, Any] | None:
    """Get a single entity by label and ID."""
    validate_label(label)
    query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
    result = client.ro_query(query, params={"id": entity_id})
    if not result.result_set:
        return None
    node = result.result_set[0][0]
    props = dict(node.properties)
    props["label"] = label
    return props


def get_entity_any_label(client: FalkorDBClient, entity_id: str) -> dict[str, Any] | None:
    """Get an entity by ID regardless of label."""
    query = "MATCH (n {id: $id}) RETURN n, labels(n) AS lbls"
    result = client.ro_query(query, params={"id": entity_id})
    if not result.result_set:
        return None
    node = result.result_set[0][0]
    labels = result.result_set[0][1]
    props = dict(node.properties)
    props["label"] = labels[0] if labels else "Unknown"
    return props


def update_entity(
    client: FalkorDBClient, label: str, entity_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    """Update entity properties."""
    validate_label(label)
    updates["updated_at"] = _now()
    for key, val in updates.items():
        if isinstance(val, list):
            updates[key] = json.dumps(val)

    updates = {k: v for k, v in updates.items() if v is not None}
    set_clauses = ", ".join(f"n.{k} = ${k}" for k in updates)
    query = f"MATCH (n:{label} {{id: $id}}) SET {set_clauses} RETURN n"
    params = {"id": entity_id, **updates}
    result = client.query(query, params=params)
    if not result.result_set:
        return None
    node = result.result_set[0][0]
    props = dict(node.properties)
    props["label"] = label
    return props


def delete_entity(client: FalkorDBClient, label: str, entity_id: str) -> bool:
    """Delete an entity and all its relationships."""
    validate_label(label)
    query = f"MATCH (n:{label} {{id: $id}}) DETACH DELETE n"
    result = client.query(query, params={"id": entity_id})
    deleted = result.nodes_deleted > 0 if hasattr(result, "nodes_deleted") else True
    if deleted:
        logger.info("entity_deleted", label=label, id=entity_id)
    return deleted


def list_entities(
    client: FalkorDBClient,
    label: str,
    skip: int = 0,
    limit: int = 50,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """List entities of a given label with optional filters."""
    validate_label(label)
    where_clauses = []
    params: dict[str, Any] = {}

    if filters:
        for key, val in filters.items():
            if val:
                param_name = f"f_{key}"
                where_clauses.append(f"toLower(n.{key}) CONTAINS toLower(${param_name})")
                params[param_name] = str(val)

    where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"MATCH (n:{label}){where_str} RETURN n ORDER BY n.name SKIP $skip LIMIT $limit"
    params["skip"] = skip
    params["limit"] = limit

    result = client.ro_query(query, params=params)
    entities = []
    for row in result.result_set:
        props = dict(row[0].properties)
        props["label"] = label
        entities.append(props)
    return entities


def count_entities(client: FalkorDBClient, label: str) -> int:
    """Count entities of a given label."""
    validate_label(label)
    query = f"MATCH (n:{label}) RETURN count(n) AS cnt"
    result = client.ro_query(query)
    return result.result_set[0][0] if result.result_set else 0


def create_relationship(
    client: FalkorDBClient,
    source_label: str,
    source_id: str,
    target_label: str,
    target_id: str,
    rel_type: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Create a relationship between two nodes."""
    validate_label(source_label)
    validate_label(target_label)
    validate_rel_type(rel_type)
    props = properties or {}
    props["created_at"] = _now()

    # Convert lists to JSON strings
    for key, val in props.items():
        if isinstance(val, list):
            props[key] = json.dumps(val)

    clean_props = {k: v for k, v in props.items() if v != "" and v is not None}

    if clean_props:
        set_clauses = " SET " + ", ".join(f"r.{k} = $p_{k}" for k in clean_props)
        params: dict[str, Any] = {
            "src_id": source_id,
            "tgt_id": target_id,
        }
        for k, v in clean_props.items():
            params[f"p_{k}"] = v
    else:
        set_clauses = ""
        params = {"src_id": source_id, "tgt_id": target_id}

    query = (
        f"MATCH (a:{source_label} {{id: $src_id}}), (b:{target_label} {{id: $tgt_id}}) "
        f"CREATE (a)-[r:{rel_type}]->(b){set_clauses} "
        f"RETURN a.id, b.id, type(r)"
    )
    result = client.query(query, params=params)
    if not result.result_set:
        return None

    logger.info("relationship_created", type=rel_type, source=source_id, target=target_id)
    return {
        "source_id": source_id,
        "target_id": target_id,
        "source_label": source_label,
        "target_label": target_label,
        "rel_type": rel_type,
        "properties": clean_props,
    }


def get_entity_relationships(
    client: FalkorDBClient,
    entity_id: str,
    direction: str = "both",
    rel_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get all relationships for an entity."""
    if rel_type:
        validate_rel_type(rel_type)
    rel_filter = f":{rel_type}" if rel_type else ""

    if direction == "outgoing":
        query = f"MATCH (a {{id: $id}})-[r{rel_filter}]->(b) RETURN a, r, b, labels(a) AS la, labels(b) AS lb LIMIT $limit"
    elif direction == "incoming":
        query = f"MATCH (a {{id: $id}})<-[r{rel_filter}]-(b) RETURN a, r, b, labels(a) AS la, labels(b) AS lb LIMIT $limit"
    else:
        query = f"MATCH (a {{id: $id}})-[r{rel_filter}]-(b) RETURN a, r, b, labels(a) AS la, labels(b) AS lb LIMIT $limit"

    result = client.ro_query(query, params={"id": entity_id, "limit": limit})
    rels = []
    for row in result.result_set:
        a_node, rel, b_node, la, lb = row
        rels.append(
            {
                "source_id": a_node.properties.get("id"),
                "target_id": b_node.properties.get("id"),
                "source_label": la[0] if la else "",
                "target_label": lb[0] if lb else "",
                "rel_type": rel.relation,
                "properties": dict(rel.properties) if rel.properties else {},
            }
        )
    return rels


def delete_relationship(
    client: FalkorDBClient,
    source_id: str,
    target_id: str,
    rel_type: str,
) -> bool:
    """Delete a specific relationship."""
    validate_rel_type(rel_type)
    query = f"MATCH (a {{id: $src_id}})-[r:{rel_type}]->(b {{id: $tgt_id}}) DELETE r"
    result = client.query(query, params={"src_id": source_id, "tgt_id": target_id})
    deleted = (
        result.relationships_deleted > 0 if hasattr(result, "relationships_deleted") else False
    )
    if deleted:
        logger.info(
            "relationship_deleted", source_id=source_id, target_id=target_id, rel_type=rel_type
        )
    return deleted


def get_neighborhood(
    client: FalkorDBClient, entity_id: str, depth: int = 1, limit: int = 50
) -> dict[str, Any]:
    """Get the neighborhood of an entity up to N hops — returns nodes and edges."""
    query = (
        "MATCH path = (center {id: $id})-[*1.." + str(depth) + "]-(neighbor) "
        "WITH DISTINCT neighbor, center "
        "LIMIT $limit "
        "MATCH (center {id: $id})-[r]-(neighbor) "
        "RETURN center, neighbor, r, labels(center) AS lc, labels(neighbor) AS ln"
    )
    result = client.ro_query(query, params={"id": entity_id, "limit": limit})

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for row in result.result_set:
        center, neighbor, rel, lc, ln = row
        center_props = dict(center.properties)
        center_props["label"] = lc[0] if lc else "Unknown"
        nodes[center_props["id"]] = center_props

        neighbor_props = dict(neighbor.properties)
        neighbor_props["label"] = ln[0] if ln else "Unknown"
        nodes[neighbor_props["id"]] = neighbor_props

        edges.append(
            {
                "source": center_props["id"],
                "target": neighbor_props["id"],
                "rel_type": rel.relation,
                "properties": dict(rel.properties) if rel.properties else {},
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}


def search_entities(
    client: FalkorDBClient, query_text: str, labels: list[str] | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Search for entities by name across all or specific labels."""
    target_labels = labels or [
        "Person",
        "Organization",
        "Account",
        "Property",
        "Event",
        "Document",
        "Address",
    ]
    results: list[dict[str, Any]] = []
    search_lower = query_text.lower()

    for label in target_labels:
        validate_label(label)
        # Search by name or other identifying fields
        if label == "Account":
            search_field = "n.account_number"
        elif label == "Address":
            search_field = "n.full_address"
        elif label == "Event":
            search_field = "n.description"
        elif label == "Document":
            search_field = "n.title"
        else:
            search_field = "n.name"

        query = (
            f"MATCH (n:{label}) "
            f"WHERE toLower({search_field}) CONTAINS $search "
            f"RETURN n LIMIT $limit"
        )
        try:
            result = client.ro_query(query, params={"search": search_lower, "limit": limit})
            for row in result.result_set:
                props = dict(row[0].properties)
                props["label"] = label
                results.append(props)
        except Exception as e:
            logger.warning("search_label_failed", label=label, error=str(e))

    return results[:limit]
