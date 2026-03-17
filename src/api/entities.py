"""Entity CRUD API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.database.falkordb_client import db
from src.graph import queries
from src.models.entities import (
    ENTITY_LABELS,
    AccountCreate,
    AddressCreate,
    DocumentCreate,
    EventCreate,
    OrganizationCreate,
    PersonCreate,
    PropertyCreate,
)

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.get("/")
def list_all_entities(
    label: str | None = Query(None, description="Filter by entity label"),
    q: str | None = Query(None, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """List entities with optional filtering."""
    if q:
        labels = [label] if label and label in ENTITY_LABELS else None
        results = queries.search_entities(db, q, labels=labels, limit=limit)
        return {"entities": results, "total": len(results)}

    if label and label not in ENTITY_LABELS:
        raise HTTPException(400, f"Invalid label. Must be one of: {ENTITY_LABELS}")

    if label:
        entities = queries.list_entities(db, label, skip=skip, limit=limit)
        total = queries.count_entities(db, label)
    else:
        entities = []
        total = 0
        per_label = max(limit // len(ENTITY_LABELS), 5)
        for lbl in ENTITY_LABELS:
            ents = queries.list_entities(db, lbl, skip=0, limit=per_label)
            entities.extend(ents)
            total += queries.count_entities(db, lbl)

    return {"entities": entities, "total": total}


@router.get("/{entity_id}")
def get_entity(entity_id: str) -> dict[str, Any]:
    """Get a single entity by ID."""
    entity = queries.get_entity_any_label(db, entity_id)
    if not entity:
        raise HTTPException(404, "Entity not found")
    return entity


@router.get("/{entity_id}/relationships")
def get_entity_relationships(
    entity_id: str,
    direction: str = Query("both", pattern="^(both|incoming|outgoing)$"),
    rel_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Get all relationships for an entity."""
    entity = queries.get_entity_any_label(db, entity_id)
    if not entity:
        raise HTTPException(404, "Entity not found")
    return queries.get_entity_relationships(
        db, entity_id, direction=direction, rel_type=rel_type, limit=limit
    )


@router.get("/{entity_id}/neighborhood")
def get_neighborhood(
    entity_id: str,
    depth: int = Query(1, ge=1, le=4),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get the graph neighborhood of an entity."""
    entity = queries.get_entity_any_label(db, entity_id)
    if not entity:
        raise HTTPException(404, "Entity not found")
    return queries.get_neighborhood(db, entity_id, depth=depth, limit=limit)


@router.post("/person")
def create_person(data: PersonCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Person", data.model_dump())


@router.post("/organization")
def create_organization(data: OrganizationCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Organization", data.model_dump())


@router.post("/account")
def create_account(data: AccountCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Account", data.model_dump())


@router.post("/property")
def create_property(data: PropertyCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Property", data.model_dump())


@router.post("/event")
def create_event(data: EventCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Event", data.model_dump())


@router.post("/document")
def create_document(data: DocumentCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Document", data.model_dump())


@router.post("/address")
def create_address(data: AddressCreate) -> dict[str, Any]:
    return queries.create_entity(db, "Address", data.model_dump())


@router.put("/{label}/{entity_id}")
def update_entity(label: str, entity_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update an entity's properties."""
    if label not in ENTITY_LABELS:
        raise HTTPException(400, f"Invalid label: {label}")
    result = queries.update_entity(db, label, entity_id, updates)
    if not result:
        raise HTTPException(404, "Entity not found")
    return result


@router.delete("/{label}/{entity_id}")
def delete_entity(label: str, entity_id: str) -> dict[str, str]:
    """Delete an entity and all its relationships."""
    if label not in ENTITY_LABELS:
        raise HTTPException(400, f"Invalid label: {label}")
    deleted = queries.delete_entity(db, label, entity_id)
    if not deleted:
        raise HTTPException(404, "Entity not found")
    return {"status": "deleted", "id": entity_id}
