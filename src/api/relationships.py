"""Relationship CRUD API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.database.falkordb_client import db
from src.graph import queries
from src.models.relationships import VALID_REL_TYPES, GenericRelationshipCreate

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.post("/")
def create_relationship(data: GenericRelationshipCreate) -> dict[str, Any]:
    """Create a relationship between two entities."""
    if data.rel_type not in VALID_REL_TYPES:
        raise HTTPException(400, f"Invalid relationship type. Must be one of: {VALID_REL_TYPES}")

    # Verify both entities exist
    source = queries.get_entity_any_label(db, data.source_id)
    if not source:
        raise HTTPException(404, f"Source entity {data.source_id} not found")

    target = queries.get_entity_any_label(db, data.target_id)
    if not target:
        raise HTTPException(404, f"Target entity {data.target_id} not found")

    result = queries.create_relationship(
        db,
        source_label=data.source_label,
        source_id=data.source_id,
        target_label=data.target_label,
        target_id=data.target_id,
        rel_type=data.rel_type,
        properties=data.properties,
    )
    if not result:
        raise HTTPException(500, "Failed to create relationship")
    return result


@router.delete("/")
def delete_relationship(source_id: str, target_id: str, rel_type: str) -> dict[str, str]:
    """Delete a specific relationship."""
    if rel_type not in VALID_REL_TYPES:
        raise HTTPException(400, f"Invalid relationship type: {rel_type}")
    deleted = queries.delete_relationship(db, source_id, target_id, rel_type)
    if not deleted:
        raise HTTPException(404, "Relationship not found")
    return {"status": "deleted"}
