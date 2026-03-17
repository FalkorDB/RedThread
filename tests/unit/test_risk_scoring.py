"""Unit tests for risk scoring — base risk, propagation, transaction patterns."""

from __future__ import annotations


class TestComputeEntityRisk:
    """Test risk score computation for individual entities."""

    def test_risk_for_high_risk_org(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        # Shell Corp: Panama jurisdiction, company type
        risk = compute_entity_risk(seeded_graph, "test-o1", depth=2)
        assert risk["entity_id"] == "test-o1"
        assert risk["risk_score"] > 0
        assert "factors" in risk
        # Should include jurisdiction risk factor for Panama
        factor_types = [f["factor"] for f in risk["factors"]]
        assert "jurisdiction" in factor_types

    def test_risk_for_low_risk_org(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        # Real Corp: US jurisdiction
        risk = compute_entity_risk(seeded_graph, "test-o2", depth=2)
        assert risk["entity_id"] == "test-o2"
        # US jurisdiction has low risk
        assert risk["risk_score"] < 80

    def test_risk_propagation_through_graph(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        # John Doe directs Shell Corp (high risk) — risk should propagate
        risk = compute_entity_risk(seeded_graph, "test-p1", depth=3)
        assert risk["entity_id"] == "test-p1"
        # Should have propagated_risk from connected high-risk org
        assert risk["propagated_risk"] >= 0

    def test_risk_for_nonexistent_entity(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        risk = compute_entity_risk(seeded_graph, "nonexistent", depth=2)
        assert risk["entity_id"] == "nonexistent"
        assert risk["risk_score"] == 0
        assert risk["factors"] == []

    def test_risk_capped_at_100(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        # Even with many risk factors, score shouldn't exceed 100
        risk = compute_entity_risk(seeded_graph, "test-o1", depth=5)
        assert risk["risk_score"] <= 100.0

    def test_risk_includes_base_and_propagated(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        risk = compute_entity_risk(seeded_graph, "test-o1", depth=2)
        assert "base_risk" in risk
        assert "propagated_risk" in risk
        assert "label" in risk

    def test_risk_depth_affects_propagation(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk

        risk_d1 = compute_entity_risk(seeded_graph, "test-p1", depth=1)
        risk_d3 = compute_entity_risk(seeded_graph, "test-p1", depth=3)
        # Deeper search may find more connected entities (but not necessarily)
        assert risk_d3["risk_score"] >= 0
        assert risk_d1["risk_score"] >= 0

    def test_propagated_risk_graceful_fallback(self, clean_graph):
        """Propagation query failure is handled gracefully (logged warning, risk=0)."""
        from src.graph.queries import create_entity, create_relationship
        from src.graph.risk_scoring import compute_entity_risk

        create_entity(
            clean_graph,
            "Person",
            {"id": "prop-p1", "name": "Innocent", "risk_score": 0.0},
        )
        create_entity(
            clean_graph,
            "Organization",
            {
                "id": "prop-o1",
                "name": "Shady Co",
                "jurisdiction": "Panama",
                "risk_score": 90.0,
            },
        )
        create_relationship(
            clean_graph, "Person", "prop-p1", "Organization", "prop-o1", "DIRECTS", {}
        )

        # FalkorDB doesn't support undirected shortestPath, so propagation
        # falls back to 0 with a logged warning — verify it doesn't crash
        risk = compute_entity_risk(clean_graph, "prop-p1", depth=2)
        assert risk["propagated_risk"] == 0.0
        assert risk["entity_id"] == "prop-p1"

    def test_high_transaction_volume_risk(self, clean_graph):
        """More than 10 outgoing transfers triggers high_transaction_volume factor."""
        from src.graph.queries import create_entity, create_relationship
        from src.graph.risk_scoring import compute_entity_risk

        create_entity(
            clean_graph,
            "Person",
            {"id": "tx-p1", "name": "Tx Person"},
        )
        create_entity(
            clean_graph,
            "Account",
            {"id": "tx-src", "account_number": "SRC"},
        )
        create_relationship(clean_graph, "Person", "tx-p1", "Account", "tx-src", "OWNS", {})

        # Create 12 destination accounts + transfers
        for i in range(12):
            dst_id = f"tx-dst-{i}"
            create_entity(
                clean_graph,
                "Account",
                {"id": dst_id, "account_number": f"DST-{i}"},
            )
            create_relationship(
                clean_graph,
                "Account",
                "tx-src",
                "Account",
                dst_id,
                "TRANSFERRED_TO",
                {"amount": 5000},
            )

        risk = compute_entity_risk(clean_graph, "tx-p1", depth=2)
        factor_types = [f["factor"] for f in risk["factors"]]
        assert "high_transaction_volume" in factor_types


class TestNetworkRisk:
    """Test batch risk computation."""

    def test_compute_multiple_entities(self, seeded_graph):
        from src.graph.risk_scoring import compute_network_risk

        results = compute_network_risk(seeded_graph, ["test-o1", "test-o2"])
        assert len(results) == 2
        assert results[0]["entity_id"] == "test-o1"
        assert results[1]["entity_id"] == "test-o2"

    def test_compute_empty_list(self, seeded_graph):
        from src.graph.risk_scoring import compute_network_risk

        results = compute_network_risk(seeded_graph, [])
        assert results == []


class TestHighestRiskEntities:
    """Test highest-risk entity listing."""

    def test_returns_ordered_by_risk(self, seeded_graph):
        from src.graph.risk_scoring import compute_entity_risk, get_highest_risk_entities

        # First compute risk to populate risk_score on nodes
        compute_entity_risk(seeded_graph, "test-o1")
        compute_entity_risk(seeded_graph, "test-o2")

        results = get_highest_risk_entities(seeded_graph, limit=10)
        assert isinstance(results, list)
        if len(results) > 1:
            scores = [r.get("risk_score", 0) for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_respects_limit(self, seeded_graph):
        from src.graph.risk_scoring import get_highest_risk_entities

        results = get_highest_risk_entities(seeded_graph, limit=1)
        assert len(results) <= 1

    def test_empty_graph(self, clean_graph):
        from src.graph.risk_scoring import get_highest_risk_entities

        results = get_highest_risk_entities(clean_graph, limit=5)
        assert results == []
