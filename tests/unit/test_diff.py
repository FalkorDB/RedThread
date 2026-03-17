"""Unit tests for graph diff — snapshots, comparison, and change detection."""

from __future__ import annotations

import pytest


class TestSnapshotCurrentGraph:
    """Test graph snapshot creation."""

    def test_creates_snapshot(self, seeded_graph, sqlite_client):
        from src.graph.diff import snapshot_current_graph

        result = snapshot_current_graph(
            seeded_graph, sqlite_client, "inv-test-1", "Initial snapshot"
        )
        assert "snapshot_id" in result
        assert result["investigation_id"] == "inv-test-1"
        assert result["name"] == "Initial snapshot"
        assert result["node_count"] > 0
        assert result["relationship_count"] > 0

    def test_snapshot_captures_all_nodes(self, seeded_graph, sqlite_client):
        from src.graph.diff import snapshot_current_graph

        result = snapshot_current_graph(seeded_graph, sqlite_client, "inv-test-2", "Full capture")
        # seeded_graph has 8 entities
        assert result["node_count"] >= 8

    def test_snapshot_auto_creates_investigation(self, seeded_graph, sqlite_client):
        from src.graph.diff import snapshot_current_graph

        snapshot_current_graph(seeded_graph, sqlite_client, "auto-inv", "Auto snapshot")
        row = sqlite_client.fetchone("SELECT id FROM investigations WHERE id = ?", ("auto-inv",))
        assert row is not None

    def test_empty_graph_snapshot(self, clean_graph, sqlite_client):
        from src.graph.diff import snapshot_current_graph

        result = snapshot_current_graph(clean_graph, sqlite_client, "inv-empty", "Empty graph")
        assert result["node_count"] == 0
        assert result["relationship_count"] == 0


class TestListSnapshots:
    """Test snapshot listing."""

    def test_list_all_snapshots(self, seeded_graph, sqlite_client):
        from src.graph.diff import list_snapshots, snapshot_current_graph

        snapshot_current_graph(seeded_graph, sqlite_client, "inv-ls", "Snap 1")
        snapshot_current_graph(seeded_graph, sqlite_client, "inv-ls", "Snap 2")

        snaps = list_snapshots(sqlite_client)
        assert len(snaps) >= 2

    def test_list_by_investigation(self, seeded_graph, sqlite_client):
        from src.graph.diff import list_snapshots, snapshot_current_graph

        snapshot_current_graph(seeded_graph, sqlite_client, "inv-a", "Snap A")
        snapshot_current_graph(seeded_graph, sqlite_client, "inv-b", "Snap B")

        snaps_a = list_snapshots(sqlite_client, investigation_id="inv-a")
        assert len(snaps_a) >= 1
        for s in snaps_a:
            assert s["investigation_id"] == "inv-a"

    def test_list_empty(self, sqlite_client):
        from src.graph.diff import list_snapshots

        snaps = list_snapshots(sqlite_client, investigation_id="nonexistent")
        assert snaps == []


class TestGetSnapshot:
    """Test snapshot retrieval."""

    def test_get_existing_snapshot(self, seeded_graph, sqlite_client):
        from src.graph.diff import get_snapshot, snapshot_current_graph

        created = snapshot_current_graph(seeded_graph, sqlite_client, "inv-get", "Test")
        snap = get_snapshot(sqlite_client, created["snapshot_id"])
        assert snap is not None
        assert "graph_state" in snap
        assert "nodes" in snap["graph_state"]
        assert "relationships" in snap["graph_state"]

    def test_get_nonexistent_snapshot(self, sqlite_client):
        from src.graph.diff import get_snapshot

        assert get_snapshot(sqlite_client, "nonexistent") is None


class TestDiffSnapshots:
    """Test snapshot comparison."""

    def test_identical_snapshots_no_changes(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_snapshots, snapshot_current_graph

        snap1 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-df", "Before")
        snap2 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-df", "After")

        diff = diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert diff["summary"]["total_changes"] == 0
        assert diff["added_nodes"] == []
        assert diff["removed_nodes"] == []

    def test_detects_added_nodes(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_snapshots, snapshot_current_graph
        from src.graph.queries import create_entity

        snap1 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-an", "Before")

        # Add a new entity
        create_entity(seeded_graph, "Person", {"id": "diff-new", "name": "New Person"})

        snap2 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-an", "After")

        diff = diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert diff["summary"]["nodes_added"] >= 1
        added_ids = [n["id"] for n in diff["added_nodes"]]
        assert "diff-new" in added_ids

    def test_detects_removed_nodes(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_snapshots, snapshot_current_graph
        from src.graph.queries import create_entity, delete_entity

        create_entity(seeded_graph, "Person", {"id": "diff-del", "name": "Delete Me"})
        snap1 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-rn", "Before")

        delete_entity(seeded_graph, "Person", "diff-del")
        snap2 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-rn", "After")

        diff = diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert diff["summary"]["nodes_removed"] >= 1
        removed_ids = [n["id"] for n in diff["removed_nodes"]]
        assert "diff-del" in removed_ids

    def test_detects_modified_nodes(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_snapshots, snapshot_current_graph
        from src.graph.queries import update_entity

        snap1 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-mn", "Before")

        # Modify an existing entity
        update_entity(seeded_graph, "Person", "test-p1", {"name": "Updated Name"})

        snap2 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-mn", "After")

        diff = diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert diff["summary"]["nodes_modified"] >= 1

    def test_detects_added_relationships(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_snapshots, snapshot_current_graph
        from src.graph.queries import create_relationship

        snap1 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-ar", "Before")

        create_relationship(
            seeded_graph, "Person", "test-p1", "Person", "test-p2", "RELATED_TO", {}
        )

        snap2 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-ar", "After")

        diff = diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert diff["summary"]["relationships_added"] >= 1

    def test_diff_nonexistent_snapshot_raises(self, sqlite_client):
        from src.graph.diff import diff_snapshots

        with pytest.raises(ValueError, match="Snapshot not found"):
            diff_snapshots(sqlite_client, "nonexistent-a", "nonexistent-b")

    def test_diff_has_snapshot_metadata(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_snapshots, snapshot_current_graph

        snap1 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-meta", "Alpha")
        snap2 = snapshot_current_graph(seeded_graph, sqlite_client, "inv-meta", "Beta")

        diff = diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert diff["snapshot_a"]["name"] == "Alpha"
        assert diff["snapshot_b"]["name"] == "Beta"


class TestDiffCurrentVsSnapshot:
    """Test comparing live graph against a saved snapshot."""

    def test_diff_current_detects_additions(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_current_vs_snapshot, snapshot_current_graph
        from src.graph.queries import create_entity

        snap = snapshot_current_graph(seeded_graph, sqlite_client, "inv-cv", "Baseline")

        create_entity(seeded_graph, "Person", {"id": "cv-new", "name": "New After Snap"})

        diff = diff_current_vs_snapshot(seeded_graph, sqlite_client, snap["snapshot_id"])
        assert diff["compared_to"] == "current_live_graph"
        assert diff["summary"]["nodes_added"] >= 1

    def test_diff_current_nonexistent_raises(self, seeded_graph, sqlite_client):
        from src.graph.diff import diff_current_vs_snapshot

        with pytest.raises(ValueError, match="Snapshot not found"):
            diff_current_vs_snapshot(seeded_graph, sqlite_client, "nonexistent")
