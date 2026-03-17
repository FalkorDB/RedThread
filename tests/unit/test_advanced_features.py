"""Tests for temporal analysis, graph diff, and NL query features."""

from __future__ import annotations

from src.graph import diff, nlq, temporal
from src.graph.queries import create_entity, create_relationship


class TestTemporal:
    """Tests for temporal graph analysis."""

    def test_date_range_empty(self, falkordb_client, clean_graph):
        """Empty graph returns None for dates."""
        result = temporal.get_date_range(falkordb_client)
        assert result["earliest"] is None
        assert result["latest"] is None

    def test_date_range_with_data(self, falkordb_client, clean_graph):
        """Date range reflects valid_from on relationships."""
        create_entity(falkordb_client, "Person", {"id": "t-p1", "name": "Alice"})
        create_entity(falkordb_client, "Organization", {"id": "t-o1", "name": "Org A"})
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o1",
            "DIRECTS",
            {"valid_from": "2020-01-01", "valid_to": "2021-06-30"},
        )
        create_entity(falkordb_client, "Organization", {"id": "t-o2", "name": "Org B"})
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o2",
            "DIRECTS",
            {"valid_from": "2022-03-15"},
        )
        result = temporal.get_date_range(falkordb_client)
        assert result["earliest"] == "2020-01-01"
        assert result["latest"] == "2022-03-15"

    def test_graph_at_time(self, falkordb_client, clean_graph):
        """Graph at a point in time only shows active relationships."""
        create_entity(falkordb_client, "Person", {"id": "t-p1", "name": "Alice"})
        create_entity(falkordb_client, "Organization", {"id": "t-o1", "name": "Org A"})
        create_entity(falkordb_client, "Organization", {"id": "t-o2", "name": "Org B"})
        # Active from 2020-2021
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o1",
            "DIRECTS",
            {"valid_from": "2020-01-01", "valid_to": "2021-06-30"},
        )
        # Active from 2022 onward
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o2",
            "DIRECTS",
            {"valid_from": "2022-03-15"},
        )

        # At mid-2020: only the first relationship should be active
        at_2020 = temporal.get_graph_at_time(falkordb_client, "2020-06-01")
        assert at_2020["edge_count"] == 1
        assert at_2020["node_count"] == 2

        # At 2023: only the second relationship should be active (first ended)
        at_2023 = temporal.get_graph_at_time(falkordb_client, "2023-01-01")
        assert at_2023["edge_count"] == 1

    def test_changes_between(self, falkordb_client, clean_graph):
        """Changes between dates shows appeared relationships."""
        create_entity(falkordb_client, "Person", {"id": "t-p1", "name": "Alice"})
        create_entity(falkordb_client, "Organization", {"id": "t-o1", "name": "Org A"})
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o1",
            "DIRECTS",
            {"valid_from": "2020-06-15", "valid_to": "2021-12-31"},
        )
        # In range 2020-01-01 to 2020-12-31: one appeared
        changes = temporal.get_changes_between(falkordb_client, "2020-01-01", "2020-12-31")
        assert len(changes["appeared"]) == 1
        assert changes["appeared"][0]["rel_type"] == "DIRECTS"

        # Disappeared in 2021
        changes_21 = temporal.get_changes_between(falkordb_client, "2021-01-01", "2021-12-31")
        assert len(changes_21["disappeared"]) == 1

    def test_relationship_timeline(self, falkordb_client, clean_graph):
        """Timeline returns chronologically ordered relationships."""
        create_entity(falkordb_client, "Person", {"id": "t-p1", "name": "Alice"})
        create_entity(falkordb_client, "Organization", {"id": "t-o1", "name": "Org A"})
        create_entity(falkordb_client, "Organization", {"id": "t-o2", "name": "Org B"})
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o2",
            "DIRECTS",
            {"valid_from": "2022-01-01"},
        )
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o1",
            "DIRECTS",
            {"valid_from": "2020-01-01"},
        )
        timeline = temporal.get_relationship_timeline(falkordb_client)
        assert len(timeline) == 2
        assert timeline[0]["valid_from"] <= timeline[1]["valid_from"]

    def test_entity_temporal_profile(self, falkordb_client, clean_graph):
        """Entity temporal profile returns all dated events for that entity."""
        create_entity(falkordb_client, "Person", {"id": "t-p1", "name": "Alice"})
        create_entity(falkordb_client, "Organization", {"id": "t-o1", "name": "Org A"})
        create_relationship(
            falkordb_client,
            "Person",
            "t-p1",
            "Organization",
            "t-o1",
            "DIRECTS",
            {"valid_from": "2020-01-01", "valid_to": "2021-06-30"},
        )
        profile = temporal.get_entity_temporal_profile(falkordb_client, "t-p1")
        assert profile["total_events"] == 1
        assert profile["events"][0]["rel_type"] == "DIRECTS"


class TestDiff:
    """Tests for graph diff engine."""

    def test_snapshot_and_diff_no_changes(self, falkordb_client, clean_graph, sqlite_client):
        """Snapshotting twice without changes shows zero diff."""
        create_entity(falkordb_client, "Person", {"id": "d-p1", "name": "Bob"})
        snap1 = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-1")
        snap2 = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-2")

        result = diff.diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert result["summary"]["total_changes"] == 0

    def test_snapshot_diff_added_node(self, falkordb_client, clean_graph, sqlite_client):
        """Adding a node between snapshots shows it in diff."""
        create_entity(falkordb_client, "Person", {"id": "d-p1", "name": "Bob"})
        snap1 = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-1")

        create_entity(falkordb_client, "Organization", {"id": "d-o1", "name": "Org X"})
        snap2 = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-2")

        result = diff.diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert result["summary"]["nodes_added"] == 1
        assert result["added_nodes"][0]["id"] == "d-o1"

    def test_snapshot_diff_removed_rel(self, falkordb_client, clean_graph, sqlite_client):
        """Removing a relationship between snapshots shows it in diff."""
        create_entity(falkordb_client, "Person", {"id": "d-p1", "name": "Bob"})
        create_entity(falkordb_client, "Organization", {"id": "d-o1", "name": "Org X"})
        create_relationship(
            falkordb_client, "Person", "d-p1", "Organization", "d-o1", "DIRECTS", {}
        )
        snap1 = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-1")

        # Delete the relationship
        falkordb_client.query(
            "MATCH (a:Person {id: 'd-p1'})-[r:DIRECTS]->(b:Organization {id: 'd-o1'}) DELETE r"
        )
        snap2 = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-2")

        result = diff.diff_snapshots(sqlite_client, snap1["snapshot_id"], snap2["snapshot_id"])
        assert result["summary"]["relationships_removed"] == 1

    def test_list_snapshots(self, falkordb_client, clean_graph, sqlite_client):
        """List snapshots returns created snapshots."""
        create_entity(falkordb_client, "Person", {"id": "d-p1", "name": "Bob"})
        diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-a")
        diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-b")

        snapshots = diff.list_snapshots(sqlite_client, "inv-1")
        assert len(snapshots) >= 2

    def test_diff_current_vs_snapshot(self, falkordb_client, clean_graph, sqlite_client):
        """Diff current graph vs snapshot works."""
        create_entity(falkordb_client, "Person", {"id": "d-p1", "name": "Bob"})
        snap = diff.snapshot_current_graph(falkordb_client, sqlite_client, "inv-1", "snap-1")

        create_entity(falkordb_client, "Organization", {"id": "d-o1", "name": "New Org"})
        result = diff.diff_current_vs_snapshot(falkordb_client, sqlite_client, snap["snapshot_id"])
        assert result["summary"]["nodes_added"] == 1


class TestNLQ:
    """Tests for natural language query translation."""

    def test_safety_check_rejects_write(self):
        """Write queries are rejected."""
        assert nlq._is_write_query("CREATE (n:Person {name: 'test'})") is True
        assert nlq._is_write_query("MATCH (n) DELETE n") is True
        assert nlq._is_write_query("MATCH (n) SET n.name = 'test'") is True
        assert nlq._is_write_query("MATCH (n) MERGE (m:Person)") is True

    def test_safety_check_allows_read(self):
        """Read queries are allowed."""
        assert nlq._is_write_query("MATCH (n:Person) RETURN n LIMIT 10") is False
        assert nlq._is_write_query("MATCH (a)-[r]->(b) RETURN a, type(r), b") is False

    def test_translate_without_api_key(self):
        """Translation gracefully fails without API key."""
        result = nlq.translate_to_cypher("Show me all persons")
        assert result["error"] is not None
        assert "LLM not configured" in result["error"]

    def test_execute_without_api_key(self, falkordb_client, clean_graph):
        """Execution gracefully fails without API key."""
        result = nlq.execute_nl_query(falkordb_client, "Show me all persons")
        assert result["error"] is not None

    def test_example_queries_exist(self):
        """Example queries are populated."""
        assert len(nlq.EXAMPLE_QUERIES) >= 5

    def test_format_result_handles_primitives(self):
        """Format result handles simple values."""

        class MockResult:
            header = ["name", "count"]
            result_set = [["Alice", 5], ["Bob", 3]]

        rows = nlq._format_result(MockResult())
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[0]["count"] == 5
