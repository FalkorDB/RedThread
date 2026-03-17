"""Graph diff engine — compare two snapshots to surface changes."""

from __future__ import annotations

import json
from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient
from src.database.sqlite_client import SQLiteClient

logger = structlog.get_logger(__name__)


def _node_display_name(node: dict) -> str:
    """Consistent display name for a node in diff output."""
    return node.get("name") or node.get("account_number") or node.get("id", "unknown")


def snapshot_current_graph(
    client: FalkorDBClient,
    sqlite: SQLiteClient,
    investigation_id: str,
    name: str,
) -> dict[str, Any]:
    """Take a full snapshot of the current graph state for an investigation.

    Captures all nodes and relationships with their properties.
    If the investigation doesn't exist, creates it automatically.
    """
    # Auto-create investigation if it doesn't exist
    existing = sqlite.fetchone("SELECT id FROM investigations WHERE id = ?", (investigation_id,))
    if not existing:
        sqlite.execute(
            "INSERT INTO investigations (id, name, description) VALUES (?, ?, ?)",
            (investigation_id, investigation_id, "Auto-created for snapshot"),
        )
        sqlite.commit()

    # Get all nodes
    node_q = "MATCH (n) RETURN n, labels(n) AS lbls"
    node_res = client.ro_query(node_q)
    nodes = []
    for row in node_res.result_set:
        props = dict(row[0].properties)
        props["_label"] = row[1][0] if row[1] else "Unknown"
        nodes.append(props)

    # Get all relationships
    rel_q = "MATCH (a)-[r]->(b) RETURN a.id, b.id, type(r) AS rel_type, properties(r) AS props"
    rel_res = client.ro_query(rel_q)
    rels = []
    for row in rel_res.result_set:
        rels.append(
            {
                "source_id": row[0],
                "target_id": row[1],
                "rel_type": row[2],
                "properties": dict(row[3]) if row[3] else {},
            }
        )

    graph_state = {"nodes": nodes, "relationships": rels}

    import uuid

    snapshot_id = f"snap-{uuid.uuid4().hex[:8]}"
    sqlite.execute(
        "INSERT INTO investigation_snapshots (id, investigation_id, name, graph_state) "
        "VALUES (?, ?, ?, ?)",
        (snapshot_id, investigation_id, name, json.dumps(graph_state)),
    )
    sqlite.commit()

    logger.info(
        "snapshot_created",
        snapshot_id=snapshot_id,
        nodes=len(nodes),
        rels=len(rels),
    )

    return {
        "snapshot_id": snapshot_id,
        "investigation_id": investigation_id,
        "name": name,
        "node_count": len(nodes),
        "relationship_count": len(rels),
    }


def list_snapshots(
    sqlite: SQLiteClient,
    investigation_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all snapshots, optionally filtered by investigation."""
    if investigation_id:
        rows = sqlite.fetchall(
            "SELECT id, investigation_id, name, created_at, "
            "  length(graph_state) AS state_size "
            "FROM investigation_snapshots "
            "WHERE investigation_id = ? "
            "ORDER BY created_at DESC",
            (investigation_id,),
        )
    else:
        rows = sqlite.fetchall(
            "SELECT id, investigation_id, name, created_at, "
            "  length(graph_state) AS state_size "
            "FROM investigation_snapshots "
            "ORDER BY created_at DESC"
        )
    return rows


def get_snapshot(sqlite: SQLiteClient, snapshot_id: str) -> dict[str, Any] | None:
    """Get a snapshot with its full graph state."""
    row = sqlite.fetchone(
        "SELECT id, investigation_id, name, graph_state, created_at "
        "FROM investigation_snapshots WHERE id = ?",
        (snapshot_id,),
    )
    if not row:
        return None
    row["graph_state"] = json.loads(row["graph_state"])
    return row


def diff_snapshots(
    sqlite: SQLiteClient,
    snapshot_id_a: str,
    snapshot_id_b: str,
) -> dict[str, Any]:
    """Compare two snapshots and return the differences.

    Returns:
      - added_nodes: nodes in B but not in A
      - removed_nodes: nodes in A but not in B
      - added_relationships: relationships in B but not in A
      - removed_relationships: relationships in A but not in B
      - modified_nodes: nodes present in both but with changed properties
    """
    snap_a = get_snapshot(sqlite, snapshot_id_a)
    snap_b = get_snapshot(sqlite, snapshot_id_b)

    if not snap_a or not snap_b:
        missing = snapshot_id_a if not snap_a else snapshot_id_b
        raise ValueError(f"Snapshot not found: {missing}")

    state_a = snap_a["graph_state"]
    state_b = snap_b["graph_state"]

    # Index nodes by ID
    nodes_a = {n["id"]: n for n in state_a["nodes"]}
    nodes_b = {n["id"]: n for n in state_b["nodes"]}

    ids_a = set(nodes_a.keys())
    ids_b = set(nodes_b.keys())

    added_nodes = [nodes_b[nid] for nid in (ids_b - ids_a)]
    removed_nodes = [nodes_a[nid] for nid in (ids_a - ids_b)]

    # Find modified nodes (same ID, different properties)
    modified_nodes = []
    for nid in ids_a & ids_b:
        a_props = {k: v for k, v in nodes_a[nid].items() if k not in ("created_at", "updated_at")}
        b_props = {k: v for k, v in nodes_b[nid].items() if k not in ("created_at", "updated_at")}
        if a_props != b_props:
            changes = {}
            all_keys = set(a_props.keys()) | set(b_props.keys())
            for key in all_keys:
                old_val = a_props.get(key)
                new_val = b_props.get(key)
                if old_val != new_val:
                    changes[key] = {"old": old_val, "new": new_val}
            if changes:
                modified_nodes.append(
                    {
                        "id": nid,
                        "name": _node_display_name(nodes_b[nid]),
                        "label": nodes_b[nid].get("_label", "Unknown"),
                        "changes": changes,
                    }
                )

    # Index relationships by composite key
    def _rel_key(r: dict) -> str:
        return f"{r['source_id']}|{r['rel_type']}|{r['target_id']}"

    rels_a = {_rel_key(r): r for r in state_a["relationships"]}
    rels_b = {_rel_key(r): r for r in state_b["relationships"]}

    rkeys_a = set(rels_a.keys())
    rkeys_b = set(rels_b.keys())

    added_rels = [rels_b[k] for k in (rkeys_b - rkeys_a)]
    removed_rels = [rels_a[k] for k in (rkeys_a - rkeys_b)]

    diff = {
        "snapshot_a": {
            "id": snapshot_id_a,
            "name": snap_a["name"],
            "created_at": snap_a["created_at"],
        },
        "snapshot_b": {
            "id": snapshot_id_b,
            "name": snap_b["name"],
            "created_at": snap_b["created_at"],
        },
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "modified_nodes": modified_nodes,
        "added_relationships": added_rels,
        "removed_relationships": removed_rels,
        "summary": {
            "nodes_added": len(added_nodes),
            "nodes_removed": len(removed_nodes),
            "nodes_modified": len(modified_nodes),
            "relationships_added": len(added_rels),
            "relationships_removed": len(removed_rels),
            "total_changes": (
                len(added_nodes)
                + len(removed_nodes)
                + len(modified_nodes)
                + len(added_rels)
                + len(removed_rels)
            ),
        },
    }

    logger.info(
        "snapshot_diff",
        a=snapshot_id_a,
        b=snapshot_id_b,
        total_changes=diff["summary"]["total_changes"],
    )

    return diff


def diff_current_vs_snapshot(
    client: FalkorDBClient,
    sqlite: SQLiteClient,
    snapshot_id: str,
) -> dict[str, Any]:
    """Compare the current live graph against a saved snapshot.

    Creates a temporary snapshot of the current state and diffs it.
    """
    snap_old = get_snapshot(sqlite, snapshot_id)
    if not snap_old:
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    # Build current state without saving
    node_q = "MATCH (n) RETURN n, labels(n) AS lbls"
    node_res = client.ro_query(node_q)
    current_nodes = []
    for row in node_res.result_set:
        props = dict(row[0].properties)
        props["_label"] = row[1][0] if row[1] else "Unknown"
        current_nodes.append(props)

    rel_q = "MATCH (a)-[r]->(b) RETURN a.id, b.id, type(r) AS rel_type, properties(r) AS props"
    rel_res = client.ro_query(rel_q)
    current_rels = []
    for row in rel_res.result_set:
        current_rels.append(
            {
                "source_id": row[0],
                "target_id": row[1],
                "rel_type": row[2],
                "properties": dict(row[3]) if row[3] else {},
            }
        )

    state_old = snap_old["graph_state"]
    state_current = {"nodes": current_nodes, "relationships": current_rels}

    # Reuse the same diff logic
    nodes_a = {n["id"]: n for n in state_old["nodes"]}
    nodes_b = {n["id"]: n for n in state_current["nodes"]}

    ids_a = set(nodes_a.keys())
    ids_b = set(nodes_b.keys())

    added_nodes = [nodes_b[nid] for nid in (ids_b - ids_a)]
    removed_nodes = [nodes_a[nid] for nid in (ids_a - ids_b)]

    modified_nodes = []
    for nid in ids_a & ids_b:
        a_props = {k: v for k, v in nodes_a[nid].items() if k not in ("created_at", "updated_at")}
        b_props = {k: v for k, v in nodes_b[nid].items() if k not in ("created_at", "updated_at")}
        if a_props != b_props:
            changes = {}
            for key in set(a_props.keys()) | set(b_props.keys()):
                old_val = a_props.get(key)
                new_val = b_props.get(key)
                if old_val != new_val:
                    changes[key] = {"old": old_val, "new": new_val}
            if changes:
                modified_nodes.append(
                    {
                        "id": nid,
                        "name": _node_display_name(nodes_b[nid]),
                        "label": nodes_b[nid].get("_label", "Unknown"),
                        "changes": changes,
                    }
                )

    def _rel_key(r: dict) -> str:
        return f"{r['source_id']}|{r['rel_type']}|{r['target_id']}"

    rels_a = {_rel_key(r): r for r in state_old["relationships"]}
    rels_b = {_rel_key(r): r for r in state_current["relationships"]}

    added_rels = [rels_b[k] for k in (set(rels_b.keys()) - set(rels_a.keys()))]
    removed_rels = [rels_a[k] for k in (set(rels_a.keys()) - set(rels_b.keys()))]

    return {
        "snapshot": {
            "id": snapshot_id,
            "name": snap_old["name"],
            "created_at": snap_old["created_at"],
        },
        "compared_to": "current_live_graph",
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "modified_nodes": modified_nodes,
        "added_relationships": added_rels,
        "removed_relationships": removed_rels,
        "summary": {
            "nodes_added": len(added_nodes),
            "nodes_removed": len(removed_nodes),
            "nodes_modified": len(modified_nodes),
            "relationships_added": len(added_rels),
            "relationships_removed": len(removed_rels),
            "total_changes": (
                len(added_nodes)
                + len(removed_nodes)
                + len(modified_nodes)
                + len(added_rels)
                + len(removed_rels)
            ),
        },
    }
