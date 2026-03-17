"""Unit tests for input validation — entity labels, rel types, and error logging."""

from __future__ import annotations

from src.ingestion.validators import (
    VALID_LABELS,
    VALID_REL_TYPES,
    validate_entity_data,
    validate_relationship_data,
)


class TestEntityLabelValidation:
    """Ensure invalid entity labels are rejected at validation time."""

    def test_valid_labels_accepted(self):
        for label in VALID_LABELS:
            errors = validate_entity_data(
                label,
                {
                    "name": "Test",
                    "account_number": "A1",
                    "full_address": "Addr",
                    "event_type": "filing",
                },
            )
            # Should not contain a label error
            assert not any("Invalid label" in e for e in errors)

    def test_invalid_label_rejected(self):
        errors = validate_entity_data("Malicious", {"name": "Bad"})
        assert len(errors) >= 1
        assert any("Invalid label" in e for e in errors)

    def test_empty_label_rejected(self):
        errors = validate_entity_data("", {"name": "Bad"})
        assert len(errors) >= 1
        assert any("Invalid label" in e for e in errors)

    def test_case_sensitive_label(self):
        errors = validate_entity_data("person", {"name": "Bad"})
        assert len(errors) >= 1
        assert any("Invalid label" in e for e in errors)


class TestRelationshipTypeValidation:
    """Ensure invalid relationship types are rejected at validation time."""

    def test_valid_rel_types_accepted(self):
        base_data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "Organization",
        }
        for rel_type in VALID_REL_TYPES:
            errors = validate_relationship_data(rel_type, base_data)
            assert not any("Invalid relationship type" in e for e in errors)

    def test_invalid_rel_type_rejected(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "Organization",
        }
        errors = validate_relationship_data("HACKS_INTO", data)
        assert any("Invalid relationship type" in e for e in errors)

    def test_empty_rel_type_rejected(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "Organization",
        }
        errors = validate_relationship_data("", data)
        assert any("Invalid relationship type" in e for e in errors)

    def test_case_sensitive_rel_type(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "Organization",
        }
        errors = validate_relationship_data("owns", data)
        assert any("Invalid relationship type" in e for e in errors)


class TestEntityDataValidation:
    """Edge cases in entity data validation."""

    def test_missing_required_person_name(self):
        errors = validate_entity_data("Person", {})
        assert any("name" in e for e in errors)

    def test_missing_required_account_number(self):
        errors = validate_entity_data("Account", {})
        assert any("account_number" in e for e in errors)

    def test_missing_required_address(self):
        errors = validate_entity_data("Address", {})
        assert any("full_address" in e for e in errors)

    def test_risk_score_out_of_range(self):
        errors = validate_entity_data("Person", {"name": "Test", "risk_score": 200})
        assert any("risk_score" in e for e in errors)

    def test_risk_score_negative(self):
        errors = validate_entity_data("Person", {"name": "Test", "risk_score": -5})
        assert any("risk_score" in e for e in errors)

    def test_risk_score_not_number(self):
        errors = validate_entity_data("Person", {"name": "Test", "risk_score": "abc"})
        assert any("risk_score" in e for e in errors)

    def test_invalid_date_format(self):
        errors = validate_entity_data("Person", {"name": "Test", "dob": "not-a-date"})
        assert any("dob" in e for e in errors)

    def test_valid_date_accepted(self):
        errors = validate_entity_data("Person", {"name": "Test", "dob": "1990-05-15"})
        assert not any("dob" in e for e in errors)

    def test_string_too_long(self):
        errors = validate_entity_data("Person", {"name": "x" * 1001})
        assert any("maximum length" in e for e in errors)

    def test_property_no_required_fields(self):
        errors = validate_entity_data("Property", {})
        assert len(errors) == 0

    def test_document_no_required_fields(self):
        errors = validate_entity_data("Document", {})
        assert len(errors) == 0


class TestRelationshipDataValidation:
    """Edge cases in relationship data validation."""

    def test_missing_source_id(self):
        data = {"target_id": "t1", "source_label": "Person", "target_label": "Organization"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("source_id" in e for e in errors)

    def test_missing_target_id(self):
        data = {"source_id": "s1", "source_label": "Person", "target_label": "Organization"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("target_id" in e for e in errors)

    def test_invalid_source_label_in_relationship(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "InvalidType",
            "target_label": "Organization",
        }
        errors = validate_relationship_data("DIRECTS", data)
        assert any("source_label" in e for e in errors)

    def test_invalid_target_label_in_relationship(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "InvalidType",
        }
        errors = validate_relationship_data("DIRECTS", data)
        assert any("target_label" in e for e in errors)

    def test_transfer_negative_amount(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Account",
            "target_label": "Account",
            "amount": -500,
        }
        errors = validate_relationship_data("TRANSFERRED_TO", data)
        assert any("amount" in e.lower() for e in errors)

    def test_transfer_zero_amount(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Account",
            "target_label": "Account",
            "amount": 0,
        }
        errors = validate_relationship_data("TRANSFERRED_TO", data)
        assert any("amount" in e.lower() for e in errors)

    def test_confidence_out_of_range(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "Person",
            "confidence": 5.0,
        }
        errors = validate_relationship_data("ASSOCIATED_WITH", data)
        assert any("confidence" in e for e in errors)

    def test_share_pct_out_of_range(self):
        data = {
            "source_id": "s1",
            "target_id": "t1",
            "source_label": "Person",
            "target_label": "Account",
            "share_pct": 150,
        }
        errors = validate_relationship_data("OWNS", data)
        assert any("share_pct" in e for e in errors)
