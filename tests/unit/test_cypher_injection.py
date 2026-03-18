"""Tests for Cypher injection prevention via identifier validation."""

from __future__ import annotations

import pytest

from src.graph.cypher_utils import (
    build_rel_filter,
    validate_label,
    validate_rel_type,
    validate_rel_types,
)


class TestValidateLabel:
    def test_valid_labels(self):
        for label in [
            "Person",
            "Organization",
            "Account",
            "Property",
            "Event",
            "Document",
            "Address",
        ]:
            assert validate_label(label) == label

    def test_invalid_label_raises(self):
        with pytest.raises(ValueError, match="Invalid label"):
            validate_label("NotALabel")

    def test_injection_via_label(self):
        with pytest.raises(ValueError, match="Invalid label"):
            validate_label("Person}) DETACH DELETE (n")

    def test_empty_label(self):
        with pytest.raises(ValueError, match="Invalid label"):
            validate_label("")


class TestValidateRelType:
    def test_valid_types(self):
        for rt in ["OWNS", "DIRECTS", "TRANSFERRED_TO", "SUBSIDIARY_OF"]:
            assert validate_rel_type(rt) == rt

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid relationship type"):
            validate_rel_type("FAKE_TYPE")

    def test_injection_via_rel_type(self):
        with pytest.raises(ValueError, match="Invalid relationship type"):
            validate_rel_type("OWNS]->(b) DELETE (a)-[r")


class TestValidateRelTypes:
    def test_valid_list(self):
        result = validate_rel_types(["OWNS", "DIRECTS"])
        assert result == ["OWNS", "DIRECTS"]

    def test_empty_list(self):
        assert validate_rel_types([]) == []

    def test_one_bad_type_fails_all(self):
        with pytest.raises(ValueError, match="Invalid relationship type"):
            validate_rel_types(["OWNS", "INJECTED_TYPE"])


class TestBuildRelFilter:
    def test_none_returns_empty(self):
        assert build_rel_filter(None) == ""

    def test_empty_list_returns_empty(self):
        assert build_rel_filter([]) == ""

    def test_single_type(self):
        assert build_rel_filter(["OWNS"]) == ":OWNS"

    def test_multiple_types(self):
        result = build_rel_filter(["OWNS", "DIRECTS"])
        assert result == ":OWNS|DIRECTS"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid relationship type"):
            build_rel_filter(["OWNS", "DROP_TABLE"])


class TestInjectionViaAPI:
    """Integration tests verifying injection is blocked at the API layer."""

    def test_pathfinding_rejects_bad_rel_type(self, test_client):
        resp = test_client.get(
            "/api/analysis/paths",
            params={"source": "a", "target": "b", "rel_types": "OWNS]->(x) DELETE x//"},
        )
        assert resp.status_code == 422

    def test_shortest_path_rejects_bad_rel_type(self, test_client):
        resp = test_client.get(
            "/api/analysis/shortest-path",
            params={"source": "a", "target": "b", "rel_types": "INJECTED"},
        )
        assert resp.status_code == 422

    def test_centrality_rejects_bad_label(self, test_client):
        resp = test_client.get(
            "/api/analysis/centrality",
            params={"label": "Person}) MATCH (n) DELETE n//"},
        )
        assert resp.status_code == 422

    def test_bridges_rejects_bad_label(self, test_client):
        resp = test_client.get(
            "/api/analysis/bridges",
            params={"label": "INJECTED"},
        )
        assert resp.status_code == 422

    def test_entity_crud_rejects_bad_label(self):
        """Graph layer rejects invalid labels even from direct calls."""
        from unittest.mock import MagicMock

        from src.graph.queries import create_entity

        with pytest.raises(ValueError, match="Invalid label"):
            create_entity(MagicMock(), "INJECTED_LABEL", {"name": "test"})

    def test_search_rejects_bad_label(self):
        """Graph layer rejects invalid labels in search_entities."""
        from unittest.mock import MagicMock

        from src.graph.queries import search_entities

        with pytest.raises(ValueError, match="Invalid label"):
            search_entities(MagicMock(), "test", labels=["INJECTED"])
