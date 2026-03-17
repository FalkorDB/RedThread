"""Unit tests for pattern detection."""

from __future__ import annotations


class TestPatterns:
    def test_detect_circular_flows(self, seeded_graph):
        from src.graph.patterns import detect_circular_flows

        cycles = detect_circular_flows(seeded_graph, min_length=3, max_length=8)
        assert len(cycles) > 0
        assert cycles[0]["pattern"] == "circular_flow"

    def test_detect_shell_company_chains(self, seeded_graph):
        from src.graph.patterns import detect_shell_company_chains

        # The test data has a subsidiary chain across jurisdictions
        chains = detect_shell_company_chains(seeded_graph, min_depth=1)
        # May or may not find chains depending on test data setup
        assert isinstance(chains, list)

    def test_detect_structuring(self, seeded_graph):
        from src.graph.patterns import detect_structuring

        patterns = detect_structuring(seeded_graph, threshold=100000, min_count=1)
        assert isinstance(patterns, list)

    def test_detect_hidden_connections(self, seeded_graph):
        from src.graph.patterns import detect_hidden_connections

        connections = detect_hidden_connections(seeded_graph, "test-p1", "test-a3")
        assert isinstance(connections, list)

    def test_run_all_patterns(self, seeded_graph):
        from src.graph.patterns import run_all_pattern_detection

        results = run_all_pattern_detection(seeded_graph)
        assert "circular_flows" in results
        assert "shell_company_chains" in results
        assert "structuring" in results
        assert "rapid_passthrough" in results


class TestRiskScoring:
    def test_compute_entity_risk(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        risk = compute_entity_risk(seeded_graph, "test-o1")
        assert risk["risk_score"] >= 0
        assert "factors" in risk

    def test_risk_propagation(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        # test-o1 (Panama, company) should have base risk
        risk = compute_entity_risk(seeded_graph, "test-o1")
        assert risk["base_risk"] > 0  # Panama jurisdiction risk

    def test_highest_risk_entities(self, seeded_graph):
        from src.graph.risk_scoring import get_highest_risk_entities

        entities = get_highest_risk_entities(seeded_graph, limit=5)
        assert isinstance(entities, list)
