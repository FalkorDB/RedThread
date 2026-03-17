"""Unit tests for graph queries."""

from __future__ import annotations


class TestQueryCRUD:
    """Test entity CRUD operations against FalkorDB."""

    def test_create_and_get_person(self, clean_graph):
        from src.graph.queries import create_entity, get_entity

        result = create_entity(clean_graph, "Person", {"name": "Test Person", "nationality": "US"})
        assert result["name"] == "Test Person"
        assert "id" in result

        fetched = get_entity(clean_graph, "Person", result["id"])
        assert fetched is not None
        assert fetched["name"] == "Test Person"

    def test_create_organization(self, clean_graph):
        from src.graph.queries import create_entity, get_entity

        result = create_entity(
            clean_graph,
            "Organization",
            {
                "name": "Test Org",
                "jurisdiction": "Panama",
                "org_type": "company",
            },
        )
        assert result["name"] == "Test Org"
        fetched = get_entity(clean_graph, "Organization", result["id"])
        assert fetched["jurisdiction"] == "Panama"

    def test_update_entity(self, clean_graph):
        from src.graph.queries import create_entity, update_entity

        result = create_entity(clean_graph, "Person", {"name": "Original Name"})
        updated = update_entity(clean_graph, "Person", result["id"], {"name": "New Name"})
        assert updated["name"] == "New Name"

    def test_delete_entity(self, clean_graph):
        from src.graph.queries import create_entity, delete_entity, get_entity

        result = create_entity(clean_graph, "Person", {"name": "Delete Me"})
        assert delete_entity(clean_graph, "Person", result["id"])
        assert get_entity(clean_graph, "Person", result["id"]) is None

    def test_list_entities(self, clean_graph):
        from src.graph.queries import create_entity, list_entities

        create_entity(clean_graph, "Person", {"name": "Alice"})
        create_entity(clean_graph, "Person", {"name": "Bob"})

        entities = list_entities(clean_graph, "Person")
        assert len(entities) >= 2

    def test_search_entities(self, clean_graph):
        from src.graph.queries import create_entity, search_entities

        create_entity(clean_graph, "Person", {"name": "Viktor Kovacs"})
        create_entity(clean_graph, "Person", {"name": "Jane Smith"})

        results = search_entities(clean_graph, "kovacs")
        assert len(results) >= 1
        assert any("Kovacs" in r.get("name", "") for r in results)

    def test_create_relationship(self, clean_graph):
        from src.graph.queries import create_entity, create_relationship, get_entity_relationships

        create_entity(clean_graph, "Person", {"id": "rel-p1", "name": "Person A"})
        create_entity(clean_graph, "Organization", {"id": "rel-o1", "name": "Org A"})
        result = create_relationship(
            clean_graph, "Person", "rel-p1", "Organization", "rel-o1", "DIRECTS", {"role": "CEO"}
        )
        assert result is not None
        assert result["rel_type"] == "DIRECTS"

        rels = get_entity_relationships(clean_graph, "rel-p1")
        assert len(rels) >= 1

    def test_get_neighborhood(self, clean_graph):
        from src.graph.queries import create_entity, create_relationship, get_neighborhood

        create_entity(clean_graph, "Person", {"id": "nb-p1", "name": "Center"})
        create_entity(clean_graph, "Organization", {"id": "nb-o1", "name": "Neighbor"})
        create_relationship(clean_graph, "Person", "nb-p1", "Organization", "nb-o1", "DIRECTS", {})

        hood = get_neighborhood(clean_graph, "nb-p1", depth=1)
        assert len(hood["nodes"]) >= 2
        assert len(hood["edges"]) >= 1

    def test_get_entity_any_label(self, clean_graph):
        from src.graph.queries import create_entity, get_entity_any_label

        create_entity(clean_graph, "Account", {"id": "any-a1", "account_number": "TEST-001"})
        result = get_entity_any_label(clean_graph, "any-a1")
        assert result is not None
        assert result["account_number"] == "TEST-001"
