"""Export API endpoints — subgraph export, report generation, CSV export."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.database.falkordb_client import db
from src.graph import analytics, queries

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/subgraph")
def export_subgraph(
    entity_id: str = Query(..., description="Center entity ID"),
    depth: int = Query(2, ge=1, le=4),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """Export a subgraph around an entity as JSON (compatible with import format)."""
    entity = queries.get_entity_any_label(db, entity_id)
    if not entity:
        raise HTTPException(404, f"Entity not found: {entity_id}")

    neighborhood = queries.get_neighborhood(db, entity_id, depth=depth, limit=limit)

    entities = []
    for node in neighborhood.get("nodes", []):
        # Copy to avoid mutating the original dict
        props = {k: v for k, v in node.items() if k != "label"}
        label = node.get("label", "Unknown")
        entities.append({"label": label, "properties": props})

    relationships = []
    for edge in neighborhood.get("edges", []):
        relationships.append(
            {
                "source_id": edge["source"],
                "target_id": edge["target"],
                "source_label": "",
                "target_label": "",
                "rel_type": edge["rel_type"],
                "properties": edge.get("properties", {}),
            }
        )

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "center_entity": entity_id,
        "depth": depth,
        "entities": entities,
        "relationships": relationships,
    }


@router.get("/report")
def generate_report(
    entity_id: str = Query(..., description="Entity to report on"),
) -> dict[str, Any]:
    """Generate an investigation report for an entity."""
    entity = queries.get_entity_any_label(db, entity_id)
    if not entity:
        raise HTTPException(404, f"Entity not found: {entity_id}")

    rels = queries.get_entity_relationships(db, entity_id)
    neighborhood = queries.get_neighborhood(db, entity_id, depth=2, limit=100)
    timeline = analytics.get_entity_timeline(db, entity_id, limit=50)

    from src.graph.risk_scoring import compute_entity_risk

    risk = compute_entity_risk(db, entity_id)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "subject": entity,
        "direct_connections": len(rels),
        "network_size": len(neighborhood.get("nodes", [])),
        "risk_assessment": risk,
        "relationships": rels,
        "timeline": timeline,
        "network_summary": {
            "total_nodes": len(neighborhood.get("nodes", [])),
            "total_edges": len(neighborhood.get("edges", [])),
        },
    }

    return report


@router.get("/graph-snapshot")
def full_graph_snapshot(
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    """Export the full graph as a snapshot."""
    from src.models.entities import ENTITY_LABELS

    all_entities: list[dict] = []
    for label in ENTITY_LABELS:
        ents = queries.list_entities(db, label, skip=0, limit=limit)
        for e in ents:
            # Copy to avoid mutating the original dict
            props = {k: v for k, v in e.items() if k != "label"}
            lbl = e.get("label", label)
            all_entities.append({"label": lbl, "properties": props})

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "entities": all_entities,
        "entity_count": len(all_entities),
    }


@router.get("/entities/csv")
def export_entities_csv(
    label: str = Query(..., description="Entity label to export"),
    limit: int = Query(1000, ge=1, le=10000),
) -> StreamingResponse:
    """Export entities of a given label as a CSV file."""
    from src.graph.cypher_utils import validate_label

    validate_label(label)
    entities = queries.list_entities(db, label, skip=0, limit=limit)
    if not entities:
        raise HTTPException(404, f"No entities found for label: {label}")

    return _entities_to_csv(entities, label)


@router.get("/relationships/csv")
def export_relationships_csv(
    rel_type: str | None = Query(None, description="Filter by relationship type"),
    limit: int = Query(1000, ge=1, le=10000),
) -> StreamingResponse:
    """Export relationships as a CSV file."""
    from src.graph.cypher_utils import validate_rel_type

    if rel_type:
        validate_rel_type(rel_type)
        rel_filter = f":{rel_type}"
    else:
        rel_filter = ""

    query = (
        f"MATCH (a)-[r{rel_filter}]->(b) "
        "RETURN a.id, labels(a)[0], type(r), b.id, labels(b)[0], "
        "r.amount, r.valid_from, r.valid_to, r.created_at "
        "LIMIT $limit"
    )
    result = db.ro_query(query, params={"limit": limit})

    rows = []
    for row in result.result_set:
        rows.append(
            {
                "source_id": row[0],
                "source_label": row[1] or "",
                "rel_type": row[2],
                "target_id": row[3],
                "target_label": row[4] or "",
                "amount": row[5] if row[5] is not None else "",
                "valid_from": row[6] or "",
                "valid_to": row[7] or "",
                "created_at": row[8] or "",
            }
        )

    if not rows:
        type_desc = rel_type or "any type"
        raise HTTPException(404, f"No relationships found for: {type_desc}")

    output = io.StringIO()
    fieldnames = [
        "source_id",
        "source_label",
        "rel_type",
        "target_id",
        "target_label",
        "amount",
        "valid_from",
        "valid_to",
        "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    filename = f"relationships_{rel_type or 'all'}_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _entities_to_csv(entities: list[dict[str, Any]], label: str) -> StreamingResponse:
    """Convert entity list to a CSV streaming response."""
    if not entities:
        return StreamingResponse(
            iter([""]),
            media_type="text/csv",
        )

    # Collect all unique keys across entities
    all_keys: set[str] = set()
    for e in entities:
        all_keys.update(e.keys())

    # Put important columns first
    priority = ["id", "name", "account_number", "label"]
    fieldnames = [k for k in priority if k in all_keys]
    fieldnames += sorted(all_keys - set(priority))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(entities)

    filename = f"{label.lower()}_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
