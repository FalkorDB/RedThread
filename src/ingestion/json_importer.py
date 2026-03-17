"""JSON data importer for nested entity structures."""

from __future__ import annotations

import json
from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient
from src.graph.queries import create_entity, create_relationship
from src.ingestion.validators import validate_entity_data, validate_relationship_data

logger = structlog.get_logger(__name__)


def import_json(
    client: FalkorDBClient,
    json_content: str,
) -> dict[str, Any]:
    """Import entities and relationships from a JSON structure.

    Expected format:
    {
        "entities": [
            {"label": "Person", "properties": {"name": "...", ...}},
            ...
        ],
        "relationships": [
            {
                "source_id": "...", "target_id": "...",
                "source_label": "Person", "target_label": "Organization",
                "rel_type": "DIRECTS", "properties": {...}
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "imported_entities": 0, "imported_relationships": 0}

    results: dict[str, Any] = {
        "imported_entities": 0,
        "imported_relationships": 0,
        "entity_errors": [],
        "relationship_errors": [],
        "id_map": {},
    }

    # Import entities
    for idx, entity_data in enumerate(data.get("entities", [])):
        label = entity_data.get("label", "")
        props = entity_data.get("properties", {})
        original_id = props.get("id", "")

        errors = validate_entity_data(label, props)
        if errors:
            results["entity_errors"].append({"index": idx, "errors": errors})
            continue

        try:
            result = create_entity(client, label, props)
            new_id = result["id"]
            if original_id:
                results["id_map"][original_id] = new_id
            results["imported_entities"] += 1
        except Exception as e:
            results["entity_errors"].append({"index": idx, "errors": [str(e)]})

    # Import relationships (using id_map for cross-references)
    for idx, rel_data in enumerate(data.get("relationships", [])):
        rel_type = rel_data.get("rel_type", "")
        source_id = rel_data.get("source_id", "")
        target_id = rel_data.get("target_id", "")

        # Resolve IDs through the map
        source_id = results["id_map"].get(source_id, source_id)
        target_id = results["id_map"].get(target_id, target_id)

        rel_data_for_validation = {
            "source_id": source_id,
            "target_id": target_id,
            "source_label": rel_data.get("source_label", ""),
            "target_label": rel_data.get("target_label", ""),
        }
        errors = validate_relationship_data(rel_type, rel_data_for_validation)
        if errors:
            results["relationship_errors"].append({"index": idx, "errors": errors})
            continue

        props = rel_data.get("properties", {})
        try:
            create_relationship(
                client,
                source_label=rel_data["source_label"],
                source_id=source_id,
                target_label=rel_data["target_label"],
                target_id=target_id,
                rel_type=rel_type,
                properties=props,
            )
            results["imported_relationships"] += 1
        except Exception as e:
            results["relationship_errors"].append({"index": idx, "errors": [str(e)]})

    # Remove id_map from public results (internal use only)
    del results["id_map"]

    logger.info(
        "json_import_complete",
        entities=results["imported_entities"],
        relationships=results["imported_relationships"],
    )
    return results
