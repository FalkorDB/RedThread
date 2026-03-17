"""Entity resolution — deduplication and alias matching."""

from __future__ import annotations

import re
from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)


def normalize_name(name: str) -> str:
    """Normalize an entity name for comparison."""
    name = name.strip().lower()
    name = re.sub(r"\s+", " ", name)
    # Remove common corporate suffixes (only the trailing one)
    suffixes = [" ltd", " llc", " inc", " corp", " co.", " sa", " ag", " gmbh", " plc"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[: -len(suffix)].rstrip(" .,")
            break
    return name


def find_potential_duplicates(
    client: FalkorDBClient,
    label: str,
    name: str,
    threshold: float = 0.8,
) -> list[dict[str, Any]]:
    """Find entities that might be duplicates based on name similarity."""
    normalized = normalize_name(name)

    if label == "Account":
        query = f"MATCH (n:{label}) WHERE toLower(n.account_number) = $normalized RETURN n"
    elif label == "Address":
        query = f"MATCH (n:{label}) WHERE toLower(n.full_address) CONTAINS $normalized RETURN n"
    else:
        query = (
            f"MATCH (n:{label}) "
            f"WHERE toLower(n.name) = $normalized "
            f"OR toLower(n.name) CONTAINS $normalized "
            f"RETURN n"
        )

    result = client.ro_query(query, params={"normalized": normalized})
    matches = []
    for row in result.result_set:
        props = dict(row[0].properties)
        props["label"] = label
        matches.append(props)
    return matches


def resolve_or_create(
    client: FalkorDBClient,
    label: str,
    data: dict[str, Any],
    auto_merge: bool = False,
) -> tuple[str, bool]:
    """Find an existing entity or create a new one. Returns (entity_id, is_new)."""
    from src.graph.queries import create_entity

    name_field = (
        "account_number"
        if label == "Account"
        else ("full_address" if label == "Address" else "name")
    )
    name_value = data.get(name_field, "")

    if not name_value:
        entity = create_entity(client, label, data)
        return entity["id"], True

    duplicates = find_potential_duplicates(client, label, name_value)

    if duplicates and auto_merge:
        existing = duplicates[0]
        logger.info("entity_resolved_to_existing", label=label, name=name_value, id=existing["id"])
        return existing["id"], False

    if duplicates and not auto_merge:
        # Return first match but flag as existing
        return duplicates[0]["id"], False

    entity = create_entity(client, label, data)
    return entity["id"], True


def merge_entities(
    client: FalkorDBClient,
    keep_id: str,
    merge_id: str,
) -> bool:
    """Merge two entities — redirect all relationships from merge_id to keep_id, then delete merge_id.

    This is a graph-native operation that would require complex JOIN updates in SQL.
    """
    # Re-point all incoming relationships
    query_in = (
        "MATCH (merged {id: $merge_id})<-[r]-(other) "
        "MATCH (keep {id: $keep_id}) "
        "WITH merged, r, other, keep, type(r) AS rt, properties(r) AS rp "
        "CREATE (other)-[nr:ASSOCIATED_WITH]->(keep) "
        "SET nr = rp "
        "DELETE r "
        "RETURN count(nr)"
    )
    try:
        client.query(query_in, params={"merge_id": merge_id, "keep_id": keep_id})
    except Exception as e:
        logger.warning("merge_incoming_failed", error=str(e))

    # Re-point all outgoing relationships
    query_out = (
        "MATCH (merged {id: $merge_id})-[r]->(other) "
        "MATCH (keep {id: $keep_id}) "
        "WITH merged, r, other, keep, type(r) AS rt, properties(r) AS rp "
        "CREATE (keep)-[nr:ASSOCIATED_WITH]->(other) "
        "SET nr = rp "
        "DELETE r "
        "RETURN count(nr)"
    )
    try:
        client.query(query_out, params={"merge_id": merge_id, "keep_id": keep_id})
    except Exception as e:
        logger.warning("merge_outgoing_failed", error=str(e))

    # Delete the merged entity
    query_del = "MATCH (n {id: $merge_id}) DETACH DELETE n"
    client.query(query_del, params={"merge_id": merge_id})

    logger.info("entities_merged", keep=keep_id, merged=merge_id)
    return True
