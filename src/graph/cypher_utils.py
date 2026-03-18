"""Cypher query safety utilities — prevent injection via interpolated identifiers."""

from __future__ import annotations

import re

from src.ingestion.validators import VALID_LABELS, VALID_REL_TYPES

# Strict pattern: only uppercase letters, underscores, digits (no leading digit)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_label(label: str) -> str:
    """Validate and return a node label safe for Cypher interpolation.

    Raises ValueError if the label is not in the allowlist.
    """
    if label not in VALID_LABELS:
        raise ValueError(f"Invalid label: {label!r}. Must be one of {sorted(VALID_LABELS)}")
    return label


def validate_rel_type(rel_type: str) -> str:
    """Validate and return a relationship type safe for Cypher interpolation.

    Raises ValueError if the type is not in the allowlist.
    """
    if rel_type not in VALID_REL_TYPES:
        raise ValueError(
            f"Invalid relationship type: {rel_type!r}. Must be one of {sorted(VALID_REL_TYPES)}"
        )
    return rel_type


def validate_rel_types(rel_types: list[str]) -> list[str]:
    """Validate a list of relationship types. Returns the list unchanged.

    Raises ValueError if any type is invalid.
    """
    for rt in rel_types:
        validate_rel_type(rt)
    return rel_types


def build_rel_filter(rel_types: list[str] | None) -> str:
    """Build a safe Cypher relationship-type filter string.

    Returns e.g. ":OWNS|DIRECTS" or "" if rel_types is None/empty.
    Validates every type before interpolation.
    """
    if not rel_types:
        return ""
    validate_rel_types(rel_types)
    return ":" + "|".join(rel_types)
