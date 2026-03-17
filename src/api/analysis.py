"""Analysis API endpoints — path finding, patterns, risk."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.database.falkordb_client import db
from src.graph import analytics, pathfinding, patterns, risk_scoring

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/paths")
def find_paths(
    source: str = Query(..., description="Source entity ID"),
    target: str = Query(..., description="Target entity ID"),
    max_depth: int = Query(6, ge=1, le=8),
    rel_types: str | None = Query(None, description="Comma-separated relationship types"),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Find all paths between two entities."""
    rel_list = rel_types.split(",") if rel_types else None
    found = pathfinding.find_all_paths(
        db, source, target, max_depth=max_depth, rel_types=rel_list, limit=limit
    )
    return {"paths": found, "count": len(found), "source": source, "target": target}


@router.get("/shortest-path")
def shortest_path(
    source: str = Query(...),
    target: str = Query(...),
    rel_types: str | None = Query(None),
) -> dict[str, Any]:
    """Find the shortest path between two entities."""
    rel_list = rel_types.split(",") if rel_types else None
    path = pathfinding.find_shortest_path(db, source, target, rel_types=rel_list)
    if not path:
        return {"path": None, "found": False}
    return {"path": path, "found": True}


@router.get("/money-flow")
def trace_money_flow(
    source: str = Query(..., description="Source account ID"),
    target: str | None = Query(None, description="Target account ID (optional)"),
    max_depth: int = Query(8, ge=1, le=10),
    min_amount: float = Query(0.0, ge=0),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Trace money flow from a source account."""
    flows = pathfinding.trace_money_flow(
        db,
        source,
        target_id=target,
        max_depth=max_depth,
        min_amount=min_amount,
        limit=limit,
    )
    return {"flows": flows, "count": len(flows)}


@router.get("/reach")
def entity_reach(
    entity_id: str = Query(...),
    max_depth: int = Query(3, ge=1, le=5),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Find all entities reachable within N hops."""
    return pathfinding.find_entity_reach(db, entity_id, max_depth=max_depth, limit=limit)


@router.get("/patterns")
def detect_patterns() -> dict[str, Any]:
    """Run all pattern detection algorithms."""
    return patterns.run_all_pattern_detection(db)


@router.get("/patterns/circular-flows")
def detect_circular(
    min_length: int = Query(3, ge=2),
    max_length: int = Query(8, ge=3),
    min_amount: float = Query(0.0, ge=0),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Detect circular money flows."""
    found = patterns.detect_circular_flows(
        db,
        min_length=min_length,
        max_length=max_length,
        min_amount=min_amount,
        limit=limit,
    )
    return {"patterns": found, "count": len(found)}


@router.get("/patterns/shell-companies")
def detect_shell_companies(
    min_depth: int = Query(2, ge=1),
    max_depth: int = Query(6, ge=2),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Detect cross-jurisdiction shell company chains."""
    found = patterns.detect_shell_company_chains(
        db,
        min_depth=min_depth,
        max_depth=max_depth,
        limit=limit,
    )
    return {"patterns": found, "count": len(found)}


@router.get("/patterns/structuring")
def detect_structuring(
    threshold: float = Query(10000.0, gt=0),
    tolerance_pct: float = Query(15.0, ge=0, le=50),
    min_count: int = Query(3, ge=2),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Detect structuring (smurfing) patterns."""
    found = patterns.detect_structuring(
        db,
        threshold=threshold,
        tolerance_pct=tolerance_pct,
        min_count=min_count,
        limit=limit,
    )
    return {"patterns": found, "count": len(found)}


@router.get("/patterns/passthrough")
def detect_passthrough(
    min_amount: float = Query(1000.0, ge=0),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Detect rapid pass-through patterns."""
    found = patterns.detect_rapid_passthrough(db, min_amount=min_amount, limit=limit)
    return {"patterns": found, "count": len(found)}


@router.get("/patterns/hidden-connections")
def find_hidden_connections(
    entity1: str = Query(...),
    entity2: str = Query(...),
    max_depth: int = Query(4, ge=2, le=6),
    limit: int = Query(10, ge=1, le=20),
) -> dict[str, Any]:
    """Find hidden connections between two entities."""
    found = patterns.detect_hidden_connections(
        db,
        entity1,
        entity2,
        max_depth=max_depth,
        limit=limit,
    )
    return {"connections": found, "count": len(found)}


@router.get("/risk/{entity_id}")
def compute_risk(
    entity_id: str,
    depth: int = Query(3, ge=1, le=5),
) -> dict[str, Any]:
    """Compute risk score for an entity."""
    return risk_scoring.compute_entity_risk(db, entity_id, depth=depth)


@router.get("/risk")
def highest_risk(
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Get entities with highest risk scores."""
    return risk_scoring.get_highest_risk_entities(db, limit=limit)


@router.get("/centrality")
def centrality(
    label: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Get entities by degree centrality."""
    return analytics.degree_centrality(db, label=label, limit=limit)


@router.get("/bridges")
def bridges(
    label: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Find bridge entities connecting different groups."""
    return analytics.betweenness_proxy(db, label=label, limit=limit)


@router.get("/shared-connections")
def shared_connections(
    entity1: str = Query(...),
    entity2: str = Query(...),
    max_depth: int = Query(2, ge=1, le=3),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Find shared connections between two entities."""
    return analytics.shared_connections(
        db,
        entity1,
        entity2,
        max_depth=max_depth,
        limit=limit,
    )


@router.get("/timeline/{entity_id}")
def entity_timeline(
    entity_id: str,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Get chronological timeline of entity activity."""
    return analytics.get_entity_timeline(db, entity_id, limit=limit)


@router.get("/stats")
def graph_stats() -> dict[str, Any]:
    """Get graph summary statistics."""
    return analytics.graph_summary(db)


@router.get("/validate")
def validate_graph_data() -> dict[str, Any]:
    """Run data-quality checks on the graph.

    Detects orphaned nodes, missing names, duplicate IDs, and
    self-referencing relationships.
    """
    from src.graph.validation import validate_graph

    return validate_graph(db)
