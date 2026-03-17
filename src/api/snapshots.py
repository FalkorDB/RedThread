"""Snapshot diff API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.database.falkordb_client import db
from src.database.sqlite_client import sqlite_db
from src.graph import diff

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("/")
def create_snapshot(
    investigation_id: str = Query(..., description="Investigation ID"),
    name: str = Query(..., description="Snapshot name"),
) -> dict[str, Any]:
    """Take a snapshot of the current graph state."""
    return diff.snapshot_current_graph(db, sqlite_db, investigation_id, name)


@router.get("/")
def list_snapshots_endpoint(
    investigation_id: str | None = Query(None, description="Filter by investigation"),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """List all saved snapshots."""
    return diff.list_snapshots(sqlite_db, investigation_id, limit=limit)


@router.get("/{snapshot_id}")
def get_snapshot_endpoint(snapshot_id: str) -> dict[str, Any]:
    """Get a snapshot with its full graph state."""
    result = diff.get_snapshot(sqlite_db, snapshot_id)
    if not result:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Snapshot not found")
    return result


@router.get("/diff/compare")
def diff_snapshots_endpoint(
    snapshot_a: str = Query(..., description="First (older) snapshot ID"),
    snapshot_b: str = Query(..., description="Second (newer) snapshot ID"),
) -> dict[str, Any]:
    """Compare two snapshots and return differences."""
    return diff.diff_snapshots(sqlite_db, snapshot_a, snapshot_b)


@router.get("/diff/current")
def diff_current_endpoint(
    snapshot_id: str = Query(..., description="Snapshot to compare against"),
) -> dict[str, Any]:
    """Compare the current live graph against a saved snapshot."""
    return diff.diff_current_vs_snapshot(db, sqlite_db, snapshot_id)
