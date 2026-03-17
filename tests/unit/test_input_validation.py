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


class TestEntityTemporalValidation:
    """Ensure since <= until for entities."""

    def test_since_before_until_accepted(self):
        errors = validate_entity_data(
            "Person", {"name": "Test", "since": "2020-01-01", "until": "2023-12-31"}
        )
        assert not any("since" in e and "until" in e for e in errors)

    def test_since_equals_until_accepted(self):
        errors = validate_entity_data(
            "Person", {"name": "Test", "since": "2022-06-15", "until": "2022-06-15"}
        )
        assert not any("since" in e and "until" in e for e in errors)

    def test_since_after_until_rejected(self):
        errors = validate_entity_data(
            "Person", {"name": "Test", "since": "2025-01-01", "until": "2020-01-01"}
        )
        assert any("since must be before" in e for e in errors)

    def test_only_since_no_until_accepted(self):
        errors = validate_entity_data("Person", {"name": "Test", "since": "2020-01-01"})
        assert not any("since must be before" in e for e in errors)

    def test_only_until_no_since_accepted(self):
        errors = validate_entity_data("Person", {"name": "Test", "until": "2020-01-01"})
        assert not any("since must be before" in e for e in errors)

    def test_invalid_since_format_still_caught(self):
        errors = validate_entity_data("Person", {"name": "Test", "since": "not-a-date"})
        assert any("since" in e and "YYYY-MM-DD" in e for e in errors)


class TestRelationshipTemporalValidation:
    """Ensure valid_from <= valid_to and date formats on relationships."""

    _base = {
        "source_id": "s1",
        "target_id": "t1",
        "source_label": "Person",
        "target_label": "Organization",
    }

    def test_valid_from_before_valid_to_accepted(self):
        data = {**self._base, "valid_from": "2020-01-01", "valid_to": "2023-12-31"}
        errors = validate_relationship_data("DIRECTS", data)
        assert not any("valid_from must be before" in e for e in errors)

    def test_valid_from_equals_valid_to_accepted(self):
        data = {**self._base, "valid_from": "2022-06-15", "valid_to": "2022-06-15"}
        errors = validate_relationship_data("DIRECTS", data)
        assert not any("valid_from must be before" in e for e in errors)

    def test_valid_from_after_valid_to_rejected(self):
        data = {**self._base, "valid_from": "2025-01-01", "valid_to": "2020-01-01"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("valid_from must be before" in e for e in errors)

    def test_only_valid_from_accepted(self):
        data = {**self._base, "valid_from": "2020-01-01"}
        errors = validate_relationship_data("DIRECTS", data)
        assert not any("valid_from must be before" in e for e in errors)

    def test_only_valid_to_accepted(self):
        data = {**self._base, "valid_to": "2023-12-31"}
        errors = validate_relationship_data("DIRECTS", data)
        assert not any("valid_from must be before" in e for e in errors)

    def test_invalid_valid_from_format(self):
        data = {**self._base, "valid_from": "Jan 2020"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("valid_from" in e and "YYYY-MM-DD" in e for e in errors)

    def test_invalid_valid_to_format(self):
        data = {**self._base, "valid_to": "2020/01/01"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("valid_to" in e and "YYYY-MM-DD" in e for e in errors)

    def test_bad_format_and_bad_ordering(self):
        """Invalid format should be caught even when ordering is also wrong."""
        data = {**self._base, "valid_from": "bad", "valid_to": "2020-01-01"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("YYYY-MM-DD" in e for e in errors)

    def test_relationship_date_field_validation(self):
        """Relationship-level 'date' field is also validated."""
        data = {**self._base, "date": "not-valid"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("date" in e and "YYYY-MM-DD" in e for e in errors)

    def test_relationship_since_until_validated(self):
        """Relationship-level 'since'/'until' are validated."""
        data = {**self._base, "since": "not-a-date"}
        errors = validate_relationship_data("DIRECTS", data)
        assert any("since" in e and "YYYY-MM-DD" in e for e in errors)
