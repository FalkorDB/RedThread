"""Unit tests for entity models and validation."""

from __future__ import annotations

import pytest

from src.ingestion.validators import validate_entity_data, validate_relationship_data
from src.models.entities import AccountCreate, OrganizationCreate, PersonCreate, entity_from_node


class TestEntityModels:
    def test_person_create_valid(self):
        p = PersonCreate(name="John Doe", nationality="US", risk_score=50)
        assert p.name == "John Doe"
        assert p.risk_score == 50.0

    def test_person_create_empty_name_fails(self):
        with pytest.raises(Exception):
            PersonCreate(name="")

    def test_org_create_defaults(self):
        o = OrganizationCreate(name="Test Corp")
        assert o.org_type == "company"
        assert o.status == "active"
        assert o.risk_score == 0.0

    def test_account_create_valid(self):
        a = AccountCreate(account_number="ACC-001", institution="Bank")
        assert a.account_type == "bank"
        assert a.currency == "USD"

    def test_risk_score_bounds(self):
        with pytest.raises(Exception):
            PersonCreate(name="Test", risk_score=101)
        with pytest.raises(Exception):
            PersonCreate(name="Test", risk_score=-1)

    def test_entity_from_node(self):
        props = {"id": "p1", "name": "John", "nationality": "US", "risk_score": 30}
        entity = entity_from_node("Person", props)
        assert entity.name == "John"
        assert entity.risk_score == 30


class TestValidators:
    def test_valid_person(self):
        errors = validate_entity_data("Person", {"name": "John"})
        assert errors == []

    def test_missing_required_field(self):
        errors = validate_entity_data("Person", {})
        assert len(errors) > 0
        assert "name" in errors[0].lower()

    def test_invalid_label(self):
        errors = validate_entity_data("InvalidLabel", {"name": "Test"})
        assert len(errors) > 0

    def test_invalid_risk_score(self):
        errors = validate_entity_data("Person", {"name": "Test", "risk_score": 200})
        assert any("risk_score" in e for e in errors)

    def test_invalid_date_format(self):
        errors = validate_entity_data("Person", {"name": "Test", "dob": "not-a-date"})
        assert any("dob" in e for e in errors)

    def test_valid_relationship(self):
        errors = validate_relationship_data(
            "OWNS",
            {
                "source_id": "p1",
                "target_id": "o1",
                "source_label": "Person",
                "target_label": "Organization",
            },
        )
        assert errors == []

    def test_invalid_rel_type(self):
        errors = validate_relationship_data(
            "INVALID_TYPE",
            {
                "source_id": "p1",
                "target_id": "o1",
                "source_label": "Person",
                "target_label": "Organization",
            },
        )
        assert len(errors) > 0

    def test_missing_source_id(self):
        errors = validate_relationship_data(
            "OWNS",
            {
                "target_id": "o1",
                "source_label": "Person",
                "target_label": "Organization",
            },
        )
        assert any("source_id" in e for e in errors)

    def test_transfer_negative_amount(self):
        errors = validate_relationship_data(
            "TRANSFERRED_TO",
            {
                "source_id": "a1",
                "target_id": "a2",
                "source_label": "Account",
                "target_label": "Account",
                "amount": -100,
            },
        )
        assert any("amount" in e.lower() for e in errors)


class TestEntityResolver:
    def test_normalize_name(self):
        from src.ingestion.entity_resolver import normalize_name

        assert normalize_name("  Test Corp LLC  ") == "test corp"
        assert normalize_name("Big Company Ltd") == "big company"
        assert normalize_name("Simple Name") == "simple name"


class TestEntityFromNode:
    """Cover entity_from_node edge cases (entities.py lines 204, 208-213)."""

    def test_unknown_label_raises(self):
        with pytest.raises(ValueError, match="Unknown entity label"):
            entity_from_node("FakeLabel", {"name": "x"})

    def test_aliases_as_json_string(self):
        entity = entity_from_node("Person", {"id": "p1", "name": "Jane", "aliases": '["J","JD"]'})
        assert entity.aliases == ["J", "JD"]

    def test_aliases_as_bad_json_string(self):
        entity = entity_from_node("Person", {"id": "p2", "name": "Jane", "aliases": "not-json"})
        assert entity.aliases == []

    def test_aliases_as_list(self):
        entity = entity_from_node("Person", {"id": "p3", "name": "Jane", "aliases": ["A", "B"]})
        assert entity.aliases == ["A", "B"]
