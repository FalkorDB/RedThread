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

    def test_delete_relationship(self, clean_graph):
        from src.graph.queries import (
            create_entity,
            create_relationship,
            delete_relationship,
            get_entity_relationships,
        )

        create_entity(clean_graph, "Person", {"id": "del-p1", "name": "Src"})
        create_entity(clean_graph, "Organization", {"id": "del-o1", "name": "Tgt"})
        create_relationship(
            clean_graph, "Person", "del-p1", "Organization", "del-o1", "DIRECTS", {}
        )
        assert len(get_entity_relationships(clean_graph, "del-p1")) == 1

        deleted = delete_relationship(clean_graph, "del-p1", "del-o1", "DIRECTS")
        assert deleted is True
        assert len(get_entity_relationships(clean_graph, "del-p1")) == 0

    def test_delete_relationship_not_found(self, clean_graph):
        from src.graph.queries import delete_relationship

        deleted = delete_relationship(clean_graph, "no-src", "no-tgt", "DIRECTS")
        assert deleted is False

    def test_update_entity_with_list_property(self, clean_graph):
        """Cover line 84: json.dumps(val) for list values in update_entity."""
        from src.graph.queries import create_entity, update_entity

        entity = create_entity(clean_graph, "Person", {"name": "List Test"})
        updated = update_entity(
            clean_graph, "Person", entity["id"], {"aliases": ["Alias1", "Alias2"]}
        )
        assert updated is not None
        assert "aliases" in updated
        # Value stored as JSON string
        import json

        aliases = json.loads(updated["aliases"])
        assert aliases == ["Alias1", "Alias2"]

    def test_update_entity_nonexistent_returns_none(self, clean_graph):
        """Cover line 92: return None when entity doesn't exist."""
        from src.graph.queries import update_entity

        result = update_entity(clean_graph, "Person", "nonexistent-id", {"name": "X"})
        assert result is None

    def test_list_entities_with_filters(self, clean_graph):
        """Cover lines 123-127: list_entities with filter dict."""
        from src.graph.queries import create_entity, list_entities

        create_entity(clean_graph, "Person", {"name": "Alice Wonderland"})
        create_entity(clean_graph, "Person", {"name": "Bob Builder"})

        results = list_entities(clean_graph, "Person", filters={"name": "Alice"})
        assert len(results) >= 1
        assert all("Alice" in r.get("name", "") for r in results)

    def test_list_entities_with_empty_filter_value(self, clean_graph):
        """Cover filter loop where val is falsy — skips that filter."""
        from src.graph.queries import create_entity, list_entities

        create_entity(clean_graph, "Person", {"name": "Filter Test"})
        results = list_entities(clean_graph, "Person", filters={"name": ""})
        # Empty filter value is skipped, so we get all entities
        assert len(results) >= 1

    def test_create_relationship_with_list_property(self, clean_graph):
        """Cover line 170: json.dumps(val) for list values in create_relationship."""
        from src.graph.queries import create_entity, create_relationship

        create_entity(clean_graph, "Person", {"id": "lst-p1", "name": "P1"})
        create_entity(clean_graph, "Organization", {"id": "lst-o1", "name": "O1"})
        rel = create_relationship(
            clean_graph,
            "Person",
            "lst-p1",
            "Organization",
            "lst-o1",
            "DIRECTS",
            {"tags": ["vip", "reviewed"]},
        )
        assert rel is not None
        assert rel["rel_type"] == "DIRECTS"

    def test_create_relationship_with_empty_props(self, clean_graph):
        """Cover lines 183-184: relationship with all-empty properties (no SET clause)."""
        from src.graph.queries import create_entity, create_relationship

        create_entity(clean_graph, "Person", {"id": "emp-p1", "name": "P1"})
        create_entity(clean_graph, "Organization", {"id": "emp-o1", "name": "O1"})
        # All props are empty string or None → cleaned out → no SET clause
        rel = create_relationship(
            clean_graph,
            "Person",
            "emp-p1",
            "Organization",
            "emp-o1",
            "DIRECTS",
            {"note": "", "detail": None},
        )
        assert rel is not None

    def test_get_entity_relationships_outgoing(self, clean_graph):
        """Cover line 219: outgoing direction branch."""
        from src.graph.queries import create_entity, create_relationship, get_entity_relationships

        create_entity(clean_graph, "Person", {"id": "dir-p1", "name": "Src"})
        create_entity(clean_graph, "Organization", {"id": "dir-o1", "name": "Tgt"})
        create_relationship(
            clean_graph, "Person", "dir-p1", "Organization", "dir-o1", "DIRECTS", {}
        )

        rels = get_entity_relationships(clean_graph, "dir-p1", direction="outgoing")
        assert len(rels) >= 1

    def test_get_entity_relationships_incoming(self, clean_graph):
        """Cover line 221: incoming direction branch."""
        from src.graph.queries import create_entity, create_relationship, get_entity_relationships

        create_entity(clean_graph, "Person", {"id": "inc-p1", "name": "Src"})
        create_entity(clean_graph, "Organization", {"id": "inc-o1", "name": "Tgt"})
        create_relationship(
            clean_graph, "Person", "inc-p1", "Organization", "inc-o1", "DIRECTS", {}
        )

        # incoming from the target's perspective
        rels = get_entity_relationships(clean_graph, "inc-o1", direction="incoming")
        assert len(rels) >= 1

    def test_get_entity_relationships_with_rel_type_filter(self, clean_graph):
        """Cover line 215: rel_type filter validates and applies type."""
        from src.graph.queries import create_entity, create_relationship, get_entity_relationships

        create_entity(clean_graph, "Person", {"id": "rtf-p1", "name": "Src"})
        create_entity(clean_graph, "Organization", {"id": "rtf-o1", "name": "Tgt"})
        create_relationship(
            clean_graph, "Person", "rtf-p1", "Organization", "rtf-o1", "DIRECTS", {}
        )

        rels = get_entity_relationships(clean_graph, "rtf-p1", rel_type="DIRECTS")
        assert len(rels) >= 1

        # Different type returns none
        rels_none = get_entity_relationships(clean_graph, "rtf-p1", rel_type="OWNS")
        assert len(rels_none) == 0

    def test_search_entities_exception_handling(self, clean_graph):
        """Cover lines 341-342: search exception is logged and skipped."""
        from unittest.mock import patch

        from src.graph.queries import search_entities

        # Make ro_query raise for one label to trigger the except branch
        original_ro_query = clean_graph.ro_query

        call_count = 0

        def failing_ro_query(query, params=None):
            nonlocal call_count
            call_count += 1
            # Fail on first call, succeed on others
            if call_count == 1:
                raise RuntimeError("simulated FalkorDB error")
            return original_ro_query(query, params=params)

        with patch.object(clean_graph, "ro_query", side_effect=failing_ro_query):
            results = search_entities(clean_graph, "test_query")
        # Should still return results from labels that didn't fail
        assert isinstance(results, list)
