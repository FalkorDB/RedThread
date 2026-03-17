"""CSV data importer with column mapping."""

from __future__ import annotations

import csv
import io
from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient
from src.graph.queries import create_entity, create_relationship
from src.ingestion.validators import validate_entity_data, validate_relationship_data

logger = structlog.get_logger(__name__)


def import_entities_csv(
    client: FalkorDBClient,
    csv_content: str,
    label: str,
    column_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Import entities from CSV content.

    Args:
        client: FalkorDB client
        csv_content: Raw CSV string
        label: Entity label (Person, Organization, etc.)
        column_mapping: Optional mapping from CSV column names to entity field names
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    results = {"imported": 0, "errors": [], "skipped": 0}

    for row_num, row in enumerate(reader, start=2):
        # Apply column mapping
        if column_mapping:
            mapped = {}
            for csv_col, entity_field in column_mapping.items():
                if csv_col in row:
                    mapped[entity_field] = row[csv_col]
            data = mapped
        else:
            data = dict(row)

        # Clean empty strings
        data = {k: v.strip() for k, v in data.items() if v and v.strip()}

        # Validate
        errors = validate_entity_data(label, data)
        if errors:
            results["errors"].append({"row": row_num, "errors": errors})
            results["skipped"] += 1
            continue

        try:
            create_entity(client, label, data)
            results["imported"] += 1
        except Exception as e:
            results["errors"].append({"row": row_num, "errors": [str(e)]})
            results["skipped"] += 1

    logger.info("csv_entity_import_complete", label=label, **results)
    return results


def import_relationships_csv(
    client: FalkorDBClient,
    csv_content: str,
    rel_type: str,
    column_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Import relationships from CSV content.

    Expected columns: source_id, target_id, source_label, target_label, plus type-specific properties.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    results = {"imported": 0, "errors": [], "skipped": 0}

    for row_num, row in enumerate(reader, start=2):
        if column_mapping:
            mapped = {}
            for csv_col, field in column_mapping.items():
                if csv_col in row:
                    mapped[field] = row[csv_col]
            data = mapped
        else:
            data = dict(row)

        data = {k: v.strip() for k, v in data.items() if v and v.strip()}

        errors = validate_relationship_data(rel_type, data)
        if errors:
            results["errors"].append({"row": row_num, "errors": errors})
            results["skipped"] += 1
            continue

        props = {
            k: v
            for k, v in data.items()
            if k not in {"source_id", "target_id", "source_label", "target_label"}
        }

        try:
            create_relationship(
                client,
                source_label=data["source_label"],
                source_id=data["source_id"],
                target_label=data["target_label"],
                target_id=data["target_id"],
                rel_type=rel_type,
                properties=props,
            )
            results["imported"] += 1
        except Exception as e:
            results["errors"].append({"row": row_num, "errors": [str(e)]})
            results["skipped"] += 1

    logger.info("csv_relationship_import_complete", rel_type=rel_type, **results)
    return results
