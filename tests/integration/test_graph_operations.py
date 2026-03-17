"""Integration tests for graph operations."""

from __future__ import annotations


class TestGraphOperationsIntegration:
    """End-to-end tests for graph operations against a real FalkorDB instance."""

    def test_full_entity_lifecycle(self, clean_graph):
        from src.graph.queries import create_entity, delete_entity, get_entity, update_entity

        # Create
        entity = create_entity(
            clean_graph,
            "Person",
            {
                "name": "Lifecycle Test",
                "nationality": "Germany",
                "risk_score": 25,
            },
        )
        eid = entity["id"]
        assert get_entity(clean_graph, "Person", eid) is not None

        # Update
        updated = update_entity(clean_graph, "Person", eid, {"risk_score": 50})
        assert updated["risk_score"] == 50

        # Delete
        assert delete_entity(clean_graph, "Person", eid)
        assert get_entity(clean_graph, "Person", eid) is None

    def test_complex_path_traversal(self, seeded_graph):
        """Test multi-hop path traversal — the core graph value proposition."""
        from src.graph.pathfinding import find_all_paths

        # test-p1 → DIRECTS → test-o1 → OWNS → test-a1 → TRANSFERRED → test-a2 → OWNED_BY → test-o2 → EMPLOYED_BY → test-p2
        paths = find_all_paths(seeded_graph, "test-p1", "test-a3", max_depth=6)
        assert len(paths) > 0
        # Verify path contains expected intermediate nodes
        for path in paths:
            node_ids = [n["id"] for n in path["nodes"]]
            assert "test-p1" in node_ids or "test-a3" in node_ids

    def test_circular_flow_detection(self, seeded_graph):
        """Test cycle detection — impossible without graph."""
        from src.graph.patterns import detect_circular_flows

        cycles = detect_circular_flows(seeded_graph, min_length=3)
        assert len(cycles) > 0
        # Verify it found the test-a1 → test-a2 → test-a3 → test-a1 cycle
        account_ids = [c["start_account"] for c in cycles]
        assert any(aid.startswith("test-a") for aid in account_ids)

    def test_money_flow_aggregation(self, seeded_graph):
        """Test money flow tracing with amount aggregation."""
        from src.graph.pathfinding import trace_money_flow

        flows = trace_money_flow(seeded_graph, "test-a1")
        assert len(flows) > 0
        for flow in flows:
            assert "total_flow" in flow
            assert flow["total_flow"] > 0

    def test_risk_computation_with_propagation(self, seeded_graph):
        """Test risk score computation through the network."""
        from src.graph.risk_scoring import compute_entity_risk

        # test-o1 is in Panama (high risk jurisdiction)
        risk = compute_entity_risk(seeded_graph, "test-o1", depth=2)
        assert risk["risk_score"] > 0
        assert any(f["factor"] == "jurisdiction" for f in risk["factors"])

    def test_neighborhood_extraction(self, seeded_graph):
        """Test subgraph extraction around an entity."""
        from src.graph.queries import get_neighborhood

        hood = get_neighborhood(seeded_graph, "test-p1", depth=2, limit=50)
        assert len(hood["nodes"]) >= 3  # p1, o1, a1 at minimum
        assert len(hood["edges"]) >= 2


class TestIngestionIntegration:
    def test_csv_entity_import(self, clean_graph):
        from src.ingestion.csv_importer import import_entities_csv

        csv_data = "name,nationality,risk_score\nAlice,US,10\nBob,UK,20\n"
        result = import_entities_csv(clean_graph, csv_data, "Person")
        assert result["imported"] == 2
        assert result["skipped"] == 0

    def test_json_import(self, clean_graph):
        import json

        from src.ingestion.json_importer import import_json

        data = json.dumps(
            {
                "entities": [
                    {"label": "Person", "properties": {"id": "json-p1", "name": "JSON Person"}},
                    {"label": "Organization", "properties": {"id": "json-o1", "name": "JSON Org"}},
                ],
                "relationships": [
                    {
                        "source_id": "json-p1",
                        "target_id": "json-o1",
                        "source_label": "Person",
                        "target_label": "Organization",
                        "rel_type": "DIRECTS",
                        "properties": {"role": "CEO"},
                    }
                ],
            }
        )
        result = import_json(clean_graph, data)
        assert result["imported_entities"] == 2
        assert result["imported_relationships"] == 1

    def test_csv_with_validation_errors(self, clean_graph):
        from src.ingestion.csv_importer import import_entities_csv

        csv_data = "name,risk_score\n,50\nValid Person,30\n"
        result = import_entities_csv(clean_graph, csv_data, "Person")
        assert result["imported"] == 1
        assert result["skipped"] == 1
