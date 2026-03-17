"""Export API endpoints — subgraph export, report generation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

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
            lbl = e.pop("label", label)
            all_entities.append({"label": lbl, "properties": e})

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "entities": all_entities,
        "entity_count": len(all_entities),
    }
