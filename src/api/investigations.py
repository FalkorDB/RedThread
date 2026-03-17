"""Investigation/case management API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.database.sqlite_client import sqlite_db
from src.models.cases import InvestigationCreate, InvestigationUpdate, SnapshotCreate, TagCreate

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())[:12]


@router.get("/")
def list_investigations(
    status: str | None = Query(None, pattern="^(active|archived|closed)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """List all investigations."""
    if status:
        rows = sqlite_db.fetchall(
            "SELECT * FROM investigations WHERE status = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (status, limit, skip),
        )
    else:
        rows = sqlite_db.fetchall(
            "SELECT * FROM investigations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, skip),
        )

    for row in rows:
        count = sqlite_db.fetchone(
            "SELECT count(*) as cnt FROM investigation_entities WHERE investigation_id = ?",
            (row["id"],),
        )
        row["entity_count"] = count["cnt"] if count else 0

    return rows


@router.post("/")
def create_investigation(data: InvestigationCreate) -> dict[str, Any]:
    """Create a new investigation."""
    inv_id = _new_id()
    now = _now()
    sqlite_db.execute(
        "INSERT INTO investigations (id, name, description, status, created_at, updated_at) "
        "VALUES (?, ?, ?, 'active', ?, ?)",
        (inv_id, data.name, data.description, now, now),
    )
    sqlite_db.commit()
    return {"id": inv_id, "name": data.name, "description": data.description, "status": "active"}


@router.get("/{investigation_id}")
def get_investigation(investigation_id: str) -> dict[str, Any]:
    """Get investigation details with its entities."""
    inv = sqlite_db.fetchone("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
    if not inv:
        raise HTTPException(404, "Investigation not found")

    entities = sqlite_db.fetchall(
        "SELECT * FROM investigation_entities WHERE investigation_id = ? ORDER BY added_at",
        (investigation_id,),
    )
    inv["entities"] = entities
    return inv


@router.put("/{investigation_id}")
def update_investigation(investigation_id: str, data: InvestigationUpdate) -> dict[str, Any]:
    """Update an investigation."""
    inv = sqlite_db.fetchone("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
    if not inv:
        raise HTTPException(404, "Investigation not found")

    updates = []
    params = []
    if data.name is not None:
        updates.append("name = ?")
        params.append(data.name)
    if data.description is not None:
        updates.append("description = ?")
        params.append(data.description)
    if data.status is not None:
        updates.append("status = ?")
        params.append(data.status)

    if updates:
        updates.append("updated_at = ?")
        params.append(_now())
        params.append(investigation_id)
        sqlite_db.execute(
            f"UPDATE investigations SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )
        sqlite_db.commit()

    return sqlite_db.fetchone("SELECT * FROM investigations WHERE id = ?", (investigation_id,))


@router.delete("/{investigation_id}")
def delete_investigation(investigation_id: str) -> dict[str, str]:
    """Delete an investigation."""
    sqlite_db.execute("DELETE FROM investigations WHERE id = ?", (investigation_id,))
    sqlite_db.commit()
    return {"status": "deleted"}


@router.post("/{investigation_id}/entities")
def add_entity_to_investigation(
    investigation_id: str,
    entity_id: str = Query(...),
    entity_label: str = Query(...),
    pinned: bool = Query(False),
    notes: str = Query(""),
) -> dict[str, str]:
    """Add an entity to an investigation."""
    inv = sqlite_db.fetchone("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
    if not inv:
        raise HTTPException(404, "Investigation not found")

    try:
        sqlite_db.execute(
            "INSERT OR REPLACE INTO investigation_entities "
            "(investigation_id, entity_id, entity_label, pinned, notes, added_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (investigation_id, entity_id, entity_label, int(pinned), notes, _now()),
        )
        sqlite_db.commit()
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return {"status": "added"}


@router.delete("/{investigation_id}/entities/{entity_id}")
def remove_entity_from_investigation(investigation_id: str, entity_id: str) -> dict[str, str]:
    """Remove an entity from an investigation."""
    sqlite_db.execute(
        "DELETE FROM investigation_entities WHERE investigation_id = ? AND entity_id = ?",
        (investigation_id, entity_id),
    )
    sqlite_db.commit()
    return {"status": "removed"}


# Snapshots
@router.post("/{investigation_id}/snapshots")
def create_snapshot(investigation_id: str, data: SnapshotCreate) -> dict[str, Any]:
    """Save a snapshot of the current investigation state."""
    snap_id = _new_id()
    sqlite_db.execute(
        "INSERT INTO investigation_snapshots (id, investigation_id, name, graph_state, viewport, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (snap_id, investigation_id, data.name, data.graph_state, data.viewport, _now()),
    )
    sqlite_db.commit()
    return {"id": snap_id, "name": data.name}


@router.get("/{investigation_id}/snapshots")
def list_snapshots(
    investigation_id: str,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """List snapshots for an investigation."""
    return sqlite_db.fetchall(
        "SELECT * FROM investigation_snapshots WHERE investigation_id = ? ORDER BY created_at DESC LIMIT ?",
        (investigation_id, limit),
    )


# Tags
@router.get("/tags/all")
def list_tags(limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    return sqlite_db.fetchall("SELECT * FROM tags ORDER BY name LIMIT ?", (limit,))


@router.post("/tags")
def create_tag(data: TagCreate) -> dict[str, Any]:
    tag_id = _new_id()
    sqlite_db.execute(
        "INSERT INTO tags (id, name, color) VALUES (?, ?, ?)", (tag_id, data.name, data.color)
    )
    sqlite_db.commit()
    return {"id": tag_id, "name": data.name, "color": data.color}


@router.post("/tags/{entity_id}/{tag_id}")
def tag_entity(entity_id: str, tag_id: str) -> dict[str, str]:
    sqlite_db.execute(
        "INSERT OR IGNORE INTO entity_tags (entity_id, tag_id) VALUES (?, ?)", (entity_id, tag_id)
    )
    sqlite_db.commit()
    return {"status": "tagged"}
