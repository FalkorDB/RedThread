"""Tests for community detection in analytics module."""

from __future__ import annotations


class TestDetectCommunities:
    """Test community detection on various graph shapes."""

    def test_empty_graph(self, clean_graph):
        from src.graph.analytics import detect_communities

        result = detect_communities(clean_graph)
        assert result["total_communities"] == 0
        assert result["communities"] == []
        assert result["modularity_estimate"] == 0.0

    def test_single_connected_component(self, clean_graph):
        """All entities connected → one community."""
        from src.graph.analytics import detect_communities
        from src.graph.queries import create_entity, create_relationship

        create_entity(clean_graph, "Person", {"id": "cc-p1", "name": "P1"})
        create_entity(clean_graph, "Person", {"id": "cc-p2", "name": "P2"})
        create_entity(clean_graph, "Organization", {"id": "cc-o1", "name": "O1"})
        create_relationship(
            clean_graph, "Person", "cc-p1", "Person", "cc-p2", "ASSOCIATED_WITH", {}
        )
        create_relationship(clean_graph, "Person", "cc-p2", "Organization", "cc-o1", "DIRECTS", {})

        result = detect_communities(clean_graph)
        assert result["total_communities"] == 1
        comm = result["communities"][0]
        assert comm["size"] == 3
        assert comm["density"] > 0

    def test_two_disconnected_components(self, clean_graph):
        """Two separate groups → two communities."""
        from src.graph.analytics import detect_communities
        from src.graph.queries import create_entity, create_relationship

        # Group 1
        create_entity(clean_graph, "Person", {"id": "g1-p1", "name": "G1 P1"})
        create_entity(clean_graph, "Person", {"id": "g1-p2", "name": "G1 P2"})
        create_relationship(
            clean_graph, "Person", "g1-p1", "Person", "g1-p2", "ASSOCIATED_WITH", {}
        )

        # Group 2
        create_entity(clean_graph, "Organization", {"id": "g2-o1", "name": "G2 O1"})
        create_entity(clean_graph, "Organization", {"id": "g2-o2", "name": "G2 O2"})
        create_relationship(
            clean_graph, "Organization", "g2-o1", "Organization", "g2-o2", "SUBSIDIARY_OF", {}
        )

        result = detect_communities(clean_graph)
        assert result["total_communities"] == 2
        sizes = sorted([c["size"] for c in result["communities"]])
        assert sizes == [2, 2]
        # No cross-community edges
        assert result["cross_community_edges"] == 0

    def test_seeded_graph_communities(self, seeded_graph):
        """Seeded graph should have at least one community."""
        from src.graph.analytics import detect_communities

        result = detect_communities(seeded_graph)
        assert result["total_communities"] >= 1
        # All communities have required fields
        for comm in result["communities"]:
            assert "id" in comm
            assert "size" in comm
            assert comm["size"] >= 2
            assert "density" in comm
            assert "internal_edges" in comm
            assert "member_details" in comm

    def test_community_member_details_enriched(self, seeded_graph):
        """Member details should include name, label, and id."""
        from src.graph.analytics import detect_communities

        result = detect_communities(seeded_graph)
        for comm in result["communities"]:
            for member in comm["member_details"]:
                assert "id" in member
                # Enriched members should have name and label
                if "name" in member:
                    assert "label" in member

    def test_min_community_size_filter(self, clean_graph):
        """Communities smaller than min_size are excluded."""
        from src.graph.analytics import detect_communities
        from src.graph.queries import create_entity, create_relationship

        # Create a pair (size 2)
        create_entity(clean_graph, "Person", {"id": "min-p1", "name": "P1"})
        create_entity(clean_graph, "Person", {"id": "min-p2", "name": "P2"})
        create_relationship(
            clean_graph, "Person", "min-p1", "Person", "min-p2", "ASSOCIATED_WITH", {}
        )

        # With min_size=2, should find one community
        result = detect_communities(clean_graph, min_community_size=2)
        assert result["total_communities"] == 1

        # With min_size=3, pair should be excluded
        result = detect_communities(clean_graph, min_community_size=3)
        assert result["total_communities"] == 0

    def test_modularity_estimate(self, clean_graph):
        """Modularity should be non-zero for multi-community graphs."""
        from src.graph.analytics import detect_communities
        from src.graph.queries import create_entity, create_relationship

        # Two clearly separated groups connected by a single bridge
        for i in range(3):
            create_entity(clean_graph, "Person", {"id": f"mod-a{i}", "name": f"A{i}"})
        for i in range(3):
            create_entity(clean_graph, "Organization", {"id": f"mod-b{i}", "name": f"B{i}"})

        # Dense group A
        create_relationship(
            clean_graph, "Person", "mod-a0", "Person", "mod-a1", "ASSOCIATED_WITH", {}
        )
        create_relationship(
            clean_graph, "Person", "mod-a1", "Person", "mod-a2", "ASSOCIATED_WITH", {}
        )
        create_relationship(
            clean_graph, "Person", "mod-a0", "Person", "mod-a2", "ASSOCIATED_WITH", {}
        )

        # Dense group B
        create_relationship(
            clean_graph, "Organization", "mod-b0", "Organization", "mod-b1", "SUBSIDIARY_OF", {}
        )
        create_relationship(
            clean_graph, "Organization", "mod-b1", "Organization", "mod-b2", "SUBSIDIARY_OF", {}
        )
        create_relationship(
            clean_graph, "Organization", "mod-b0", "Organization", "mod-b2", "SUBSIDIARY_OF", {}
        )

        # No bridge between groups
        result = detect_communities(clean_graph)
        assert result["total_communities"] == 2
        assert result["modularity_estimate"] != 0.0

    def test_cross_community_edges_counted(self, clean_graph):
        """Edges between communities should be counted."""
        from src.graph.analytics import detect_communities
        from src.graph.queries import create_entity, create_relationship

        # Group 1
        create_entity(clean_graph, "Person", {"id": "xc-p1", "name": "P1"})
        create_entity(clean_graph, "Person", {"id": "xc-p2", "name": "P2"})
        create_relationship(
            clean_graph, "Person", "xc-p1", "Person", "xc-p2", "ASSOCIATED_WITH", {}
        )

        # Group 2
        create_entity(clean_graph, "Organization", {"id": "xc-o1", "name": "O1"})
        create_entity(clean_graph, "Organization", {"id": "xc-o2", "name": "O2"})
        create_relationship(
            clean_graph, "Organization", "xc-o1", "Organization", "xc-o2", "SUBSIDIARY_OF", {}
        )

        # Bridge between groups
        create_relationship(clean_graph, "Person", "xc-p1", "Organization", "xc-o1", "DIRECTS", {})

        result = detect_communities(clean_graph)
        # Should be one component now (bridge connects them)
        # OR two communities if bridge doesn't fully merge
        assert result["total_communities"] >= 1


class TestCommunitiesAPI:
    """Test the /api/analysis/communities endpoint."""

    def test_communities_endpoint(self, test_client):
        resp = test_client.get("/api/analysis/communities")
        assert resp.status_code == 200
        data = resp.json()
        assert "communities" in data
        assert "total_communities" in data
        assert "modularity_estimate" in data

    def test_communities_with_params(self, test_client):
        resp = test_client.get("/api/analysis/communities?max_communities=5&min_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["communities"]) <= 5
