"""Unit tests for entity resolver — deduplication and name normalization."""

from __future__ import annotations


class TestNormalizeName:
    """Test name normalization for entity matching."""

    def test_strips_whitespace(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("  John Doe  ") == "john doe"

    def test_lowercases(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("JOHN DOE") == "john doe"

    def test_collapses_multiple_spaces(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("John   Doe") == "john doe"

    def test_removes_ltd_suffix(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("Acme Corp Ltd") == "acme corp"

    def test_removes_llc_suffix(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("GlobalTech LLC") == "globaltech"

    def test_removes_inc_suffix(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("Megacorp Inc") == "megacorp"

    def test_removes_gmbh_suffix(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("Deutsche Firma GmbH") == "deutsche firma"

    def test_removes_plc_suffix(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("British Co PLC") == "british co"

    def test_only_removes_trailing_suffix(self):
        from src.ingestion.entity_resolver import normalize_name

        # "Inc" in the middle should NOT be removed
        assert normalize_name("Inc Holdings Group") == "inc holdings group"

    def test_empty_string(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("") == ""

    def test_no_suffix_unchanged(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("Viktor Kovacs") == "viktor kovacs"


class TestFindPotentialDuplicates:
    """Test duplicate detection against FalkorDB."""

    def test_exact_name_match(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import find_potential_duplicates

        create_entity(clean_graph, "Person", {"id": "dup-p1", "name": "John Doe"})

        matches = find_potential_duplicates(clean_graph, "Person", "John Doe")
        assert len(matches) >= 1
        assert any(m["id"] == "dup-p1" for m in matches)

    def test_case_insensitive_match(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import find_potential_duplicates

        create_entity(clean_graph, "Person", {"id": "dup-p2", "name": "Jane Smith"})

        matches = find_potential_duplicates(clean_graph, "Person", "JANE SMITH")
        assert len(matches) >= 1

    def test_no_match_returns_empty(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import find_potential_duplicates

        create_entity(clean_graph, "Person", {"id": "dup-p3", "name": "Alice"})

        matches = find_potential_duplicates(clean_graph, "Person", "Bob")
        assert len(matches) == 0

    def test_account_matches_by_number(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import find_potential_duplicates

        create_entity(clean_graph, "Account", {"id": "dup-a1", "account_number": "ACC-12345"})

        matches = find_potential_duplicates(clean_graph, "Account", "ACC-12345")
        assert len(matches) >= 1

    def test_address_matches_by_partial(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import find_potential_duplicates

        create_entity(
            clean_graph,
            "Address",
            {"id": "dup-addr1", "full_address": "123 Main St, Panama City, Panama"},
        )

        matches = find_potential_duplicates(clean_graph, "Address", "123 Main St, Panama City")
        assert len(matches) >= 1

    def test_empty_graph_returns_empty(self, clean_graph):
        from src.ingestion.entity_resolver import find_potential_duplicates

        matches = find_potential_duplicates(clean_graph, "Person", "Nobody")
        assert matches == []


class TestResolveOrCreate:
    """Test entity resolution: find existing or create new."""

    def test_creates_new_when_no_match(self, clean_graph):
        from src.ingestion.entity_resolver import resolve_or_create

        entity_id, is_new = resolve_or_create(clean_graph, "Person", {"name": "Brand New Person"})
        assert is_new is True
        assert entity_id  # Non-empty string

    def test_resolves_to_existing(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import resolve_or_create

        create_entity(clean_graph, "Person", {"id": "res-p1", "name": "Existing Person"})

        entity_id, is_new = resolve_or_create(clean_graph, "Person", {"name": "Existing Person"})
        assert is_new is False
        assert entity_id == "res-p1"

    def test_auto_merge_returns_first_match(self, clean_graph):
        from src.graph.queries import create_entity
        from src.ingestion.entity_resolver import resolve_or_create

        create_entity(clean_graph, "Person", {"id": "am-p1", "name": "Merge Target"})

        entity_id, is_new = resolve_or_create(
            clean_graph, "Person", {"name": "Merge Target"}, auto_merge=True
        )
        assert is_new is False
        assert entity_id == "am-p1"

    def test_creates_when_no_name(self, clean_graph):
        from src.ingestion.entity_resolver import resolve_or_create

        # Property type doesn't require a name field
        entity_id, is_new = resolve_or_create(
            clean_graph, "Property", {"property_type": "yacht", "value": 1000000}
        )
        assert is_new is True
        assert entity_id


class TestMergeEntities:
    """Test entity merge — relationship redirection and deletion."""

    def test_merge_redirects_relationships(self, clean_graph):
        from src.graph.queries import (
            create_entity,
            create_relationship,
            get_entity,
            get_entity_relationships,
        )
        from src.ingestion.entity_resolver import merge_entities

        create_entity(clean_graph, "Person", {"id": "m-keep", "name": "Keep Me"})
        create_entity(clean_graph, "Person", {"id": "m-merge", "name": "Merge Me"})
        create_entity(clean_graph, "Organization", {"id": "m-org", "name": "Org"})

        # Create relationship to the entity we'll merge away
        create_relationship(
            clean_graph, "Person", "m-merge", "Organization", "m-org", "DIRECTS", {}
        )

        result = merge_entities(clean_graph, "m-keep", "m-merge")
        assert result is True

        # Merged entity should be gone
        assert get_entity(clean_graph, "Person", "m-merge") is None

        # Keep entity should have the redirected relationship
        rels = get_entity_relationships(clean_graph, "m-keep")
        assert len(rels) >= 1

    def test_merge_deletes_source(self, clean_graph):
        from src.graph.queries import create_entity, get_entity
        from src.ingestion.entity_resolver import merge_entities

        create_entity(clean_graph, "Person", {"id": "md-keep", "name": "Keep"})
        create_entity(clean_graph, "Person", {"id": "md-merge", "name": "Gone"})

        merge_entities(clean_graph, "md-keep", "md-merge")
        assert get_entity(clean_graph, "Person", "md-merge") is None
        assert get_entity(clean_graph, "Person", "md-keep") is not None
