"""Input validation for imported entities and relationships."""

from __future__ import annotations

import re
from typing import Any

VALID_LABELS = {"Person", "Organization", "Account", "Property", "Event", "Document", "Address"}

VALID_REL_TYPES = {
    "OWNS",
    "DIRECTS",
    "EMPLOYED_BY",
    "TRANSFERRED_TO",
    "LOCATED_AT",
    "CONTACTED",
    "RELATED_TO",
    "PARTICIPATED_IN",
    "MENTIONED_IN",
    "SUBSIDIARY_OF",
    "ASSOCIATED_WITH",
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")


class ValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed: {'; '.join(errors)}")


def validate_entity_data(label: str, data: dict[str, Any]) -> list[str]:
    """Validate entity data before import. Returns list of error messages."""
    errors: list[str] = []

    if label not in VALID_LABELS:
        errors.append(f"Invalid label: {label}. Must be one of {VALID_LABELS}")
        return errors

    # Required fields by label
    required: dict[str, list[str]] = {
        "Person": ["name"],
        "Organization": ["name"],
        "Account": ["account_number"],
        "Property": [],
        "Event": ["event_type"],
        "Document": [],
        "Address": ["full_address"],
    }

    for field in required.get(label, []):
        if not data.get(field):
            errors.append(f"Missing required field '{field}' for {label}")

    # Type validations
    if "risk_score" in data:
        try:
            score = float(data["risk_score"])
            if score < 0 or score > 100:
                errors.append("risk_score must be between 0 and 100")
        except (ValueError, TypeError):
            errors.append("risk_score must be a number")

    if "value" in data and data["value"]:
        try:
            float(data["value"])
        except (ValueError, TypeError):
            errors.append("value must be a number")

    if "amount" in data and data["amount"]:
        try:
            float(data["amount"])
        except (ValueError, TypeError):
            errors.append("amount must be a number")

    # Date validation
    for date_field in ["dob", "date", "since", "until"]:
        if date_field in data and data[date_field]:
            if not DATE_PATTERN.match(str(data[date_field])):
                errors.append(f"{date_field} must be in YYYY-MM-DD format")

    # Ensure since <= until when both are present
    since = data.get("since")
    until = data.get("until")
    if since and until and str(since) > str(until):
        errors.append("since must be before or equal to until")

    # String length limits
    for field in ["name", "full_address", "description", "title", "summary"]:
        if field in data and data[field] and len(str(data[field])) > 1000:
            errors.append(f"{field} exceeds maximum length of 1000 characters")

    return errors


def validate_relationship_data(rel_type: str, data: dict[str, Any]) -> list[str]:
    """Validate relationship data before import."""
    errors: list[str] = []

    if rel_type not in VALID_REL_TYPES:
        errors.append(f"Invalid relationship type: {rel_type}. Must be one of {VALID_REL_TYPES}")

    if not data.get("source_id"):
        errors.append("Missing required field 'source_id'")
    if not data.get("target_id"):
        errors.append("Missing required field 'target_id'")
    if not data.get("source_label"):
        errors.append("Missing required field 'source_label'")
    if not data.get("target_label"):
        errors.append("Missing required field 'target_label'")

    if data.get("source_label") and data["source_label"] not in VALID_LABELS:
        errors.append(f"Invalid source_label: {data['source_label']}")
    if data.get("target_label") and data["target_label"] not in VALID_LABELS:
        errors.append(f"Invalid target_label: {data['target_label']}")

    # Amount validation for TRANSFERRED_TO
    if rel_type == "TRANSFERRED_TO":
        if "amount" in data:
            try:
                amt = float(data["amount"])
                if amt <= 0:
                    errors.append("Transfer amount must be positive")
            except (ValueError, TypeError):
                errors.append("Transfer amount must be a number")

    # Percentage validations
    for pct_field in ["share_pct", "ownership_pct", "confidence"]:
        if pct_field in data and data[pct_field] is not None:
            try:
                pct = float(data[pct_field])
                if pct_field == "confidence":
                    if pct < 0 or pct > 1:
                        errors.append(f"{pct_field} must be between 0 and 1")
                else:
                    if pct < 0 or pct > 100:
                        errors.append(f"{pct_field} must be between 0 and 100")
            except (ValueError, TypeError):
                errors.append(f"{pct_field} must be a number")

    # Temporal date validations
    for date_field in ["date", "since", "until", "valid_from", "valid_to"]:
        if date_field in data and data[date_field]:
            if not DATE_PATTERN.match(str(data[date_field])):
                errors.append(f"{date_field} must be in YYYY-MM-DD format")

    # Ensure valid_from <= valid_to when both are present
    vf = data.get("valid_from")
    vt = data.get("valid_to")
    if vf and vt and str(vf) > str(vt):
        errors.append("valid_from must be before or equal to valid_to")

    return errors
