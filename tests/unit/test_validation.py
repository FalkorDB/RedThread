"""Tests for graph data-quality validation."""

from __future__ import annotations


class TestValidationQueries:
    """Test individual validation queries against the test graph."""

    def test_find_orphaned_nodes(self, clean_graph):
        """An entity with no relationships is flagged as orphaned."""
        from src.graph.queries import create_entity
        from src.graph.validation import find_orphaned_nodes

        create_entity(clean_graph, "Person", {"name": "Alone"})
        orphans = find_orphaned_nodes(clean_graph)
        assert len(orphans) == 1
        assert orphans[0]["name"] == "Alone"

    def test_no_orphans_when_connected(self, clean_graph):
        from src.graph.queries import create_entity, create_relationship
        from src.graph.validation import find_orphaned_nodes

        create_entity(clean_graph, "Person", {"id": "vp1", "name": "A"})
        create_entity(clean_graph, "Organization", {"id": "vo1", "name": "B"})
        create_relationship(clean_graph, "Person", "vp1", "Organization", "vo1", "DIRECTS", {})
        orphans = find_orphaned_nodes(clean_graph)
        assert len(orphans) == 0

    def test_find_missing_names(self, clean_graph):
        from src.graph.queries import create_entity
        from src.graph.validation import find_missing_names

        # Property entities don't require a name
        create_entity(clean_graph, "Property", {"property_type": "vehicle"})
        missing = find_missing_names(clean_graph)
        # Property created without name → name defaults to ""
        assert len(missing) >= 1

    def test_find_duplicate_ids(self, clean_graph):
        from src.graph.queries import create_entity
        from src.graph.validation import find_duplicate_ids

        # Force two entities with the same id (different labels)
        create_entity(clean_graph, "Person", {"id": "dup-1", "name": "Person"})
        create_entity(clean_graph, "Organization", {"id": "dup-1", "name": "Org"})
        dupes = find_duplicate_ids(clean_graph)
        assert len(dupes) >= 1
        assert dupes[0]["id"] == "dup-1"

    def test_no_duplicates_normally(self, clean_graph):
        from src.graph.queries import create_entity
        from src.graph.validation import find_duplicate_ids

        create_entity(clean_graph, "Person", {"id": "uni-1", "name": "Unique"})
        create_entity(clean_graph, "Organization", {"id": "uni-2", "name": "Other"})
        assert find_duplicate_ids(clean_graph) == []

    def test_find_self_referencing(self, clean_graph):
        from src.graph.queries import create_entity, create_relationship
        from src.graph.validation import find_self_referencing_relationships

        create_entity(clean_graph, "Account", {"id": "sr-1", "account_number": "LOOP"})
        create_relationship(
            clean_graph, "Account", "sr-1", "Account", "sr-1", "TRANSFERRED_TO", {"amount": 100}
        )
        refs = find_self_referencing_relationships(clean_graph)
        assert len(refs) == 1
        assert refs[0]["id"] == "sr-1"

    def test_no_self_refs_normally(self, clean_graph):
        from src.graph.queries import create_entity, create_relationship
        from src.graph.validation import find_self_referencing_relationships

        create_entity(clean_graph, "Account", {"id": "nsr-1", "account_number": "A"})
        create_entity(clean_graph, "Account", {"id": "nsr-2", "account_number": "B"})
        create_relationship(
            clean_graph, "Account", "nsr-1", "Account", "nsr-2", "TRANSFERRED_TO", {}
        )
        assert find_self_referencing_relationships(clean_graph) == []


class TestValidateGraphSummary:
    """Test the combined validate_graph function."""

    def test_clean_graph_reports_clean(self, clean_graph):
        from src.graph.queries import create_entity, create_relationship
        from src.graph.validation import validate_graph

        create_entity(clean_graph, "Person", {"id": "vg-1", "name": "Clean"})
        create_entity(clean_graph, "Organization", {"id": "vg-2", "name": "Org"})
        create_relationship(clean_graph, "Person", "vg-1", "Organization", "vg-2", "DIRECTS", {})
        report = validate_graph(clean_graph)
        assert report["status"] == "clean"
        assert report["total_issues"] == 0

    def test_dirty_graph_reports_issues(self, clean_graph):
        from src.graph.queries import create_entity
        from src.graph.validation import validate_graph

        # Orphan with missing name
        create_entity(clean_graph, "Property", {"property_type": "yacht"})
        report = validate_graph(clean_graph)
        assert report["status"] == "issues_found"
        assert report["total_issues"] >= 1


class TestValidateGraphEndpoint:
    """Test the /api/analysis/validate endpoint."""

    def test_validate_endpoint(self, test_client, clean_graph):
        resp = test_client.get("/api/analysis/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert "orphaned_nodes" in data["checks"]
        assert "missing_names" in data["checks"]
        assert "duplicate_ids" in data["checks"]
        assert "self_referencing" in data["checks"]

    def test_validate_reports_issues_on_dirty_data(self, test_client, clean_graph):
        # Create orphan
        test_client.post("/api/entities/property", json={"property_type": "art"})
        resp = test_client.get("/api/analysis/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_issues"] >= 1
