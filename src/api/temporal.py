"""Temporal analysis API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.database.falkordb_client import db
from src.graph import temporal

router = APIRouter(prefix="/api/temporal", tags=["temporal"])


@router.get("/graph-at")
def graph_at_time(
    date: str = Query(..., description="Point in time (YYYY-MM-DD)"),
    entity_id: str | None = Query(None, description="Optional entity to center on"),
    limit: int = Query(200, ge=1, le=500),
) -> dict[str, Any]:
    """Get the state of the graph at a specific point in time."""
    return temporal.get_graph_at_time(db, date, entity_id=entity_id, limit=limit)


@router.get("/changes")
def changes_between(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(200, ge=1, le=500),
) -> dict[str, Any]:
    """Find relationships that appeared or disappeared between two dates."""
    return temporal.get_changes_between(db, start, end, limit=limit)


@router.get("/timeline")
def relationship_timeline(
    limit: int = Query(200, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Get all dated relationships in chronological order."""
    return temporal.get_relationship_timeline(db, limit=limit)


@router.get("/date-range")
def date_range() -> dict[str, str | None]:
    """Get the earliest and latest dates in the graph."""
    return temporal.get_date_range(db)


@router.get("/entity/{entity_id}")
def entity_temporal_profile(
    entity_id: str,
) -> dict[str, Any]:
    """Get temporal profile for an entity — when relationships formed and ended."""
    return temporal.get_entity_temporal_profile(db, entity_id)
