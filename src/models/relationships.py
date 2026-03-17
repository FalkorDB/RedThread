"""Pydantic models for graph relationships."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RelationshipBase(BaseModel):
    """Base fields shared by all relationships."""

    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    source_label: str = Field(..., description="Source entity label (Person, Organization, etc.)")
    target_label: str = Field(..., description="Target entity label")
    notes: str = ""


class OwnsCreate(RelationshipBase):
    """Person/Org owns Account/Property/Org."""

    rel_type: str = "OWNS"
    share_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    since: str = ""
    until: str = ""


class DirectsCreate(RelationshipBase):
    """Person directs Organization."""

    rel_type: str = "DIRECTS"
    role: str = "director"
    since: str = ""
    until: str = ""


class EmployedByCreate(RelationshipBase):
    """Person employed by Organization."""

    rel_type: str = "EMPLOYED_BY"
    position: str = ""
    since: str = ""
    until: str = ""


class TransferredToCreate(RelationshipBase):
    """Account transferred to Account."""

    rel_type: str = "TRANSFERRED_TO"
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    date: str = ""
    reference: str = ""


class LocatedAtCreate(RelationshipBase):
    """Person/Org located at Address."""

    rel_type: str = "LOCATED_AT"
    addr_type: str = Field(default="registered", description="registered|residential|operational")
    since: str = ""
    until: str = ""


class ContactedCreate(RelationshipBase):
    """Person contacted Person."""

    rel_type: str = "CONTACTED"
    method: str = Field(default="phone", description="phone|email|meeting|message")
    date: str = ""
    duration: str = ""


class RelatedToCreate(RelationshipBase):
    """Person related to Person."""

    rel_type: str = "RELATED_TO"
    relationship_type: str = Field(
        default="associate", description="family|business|associate|romantic"
    )
    since: str = ""


class ParticipatedInCreate(RelationshipBase):
    """Person/Org participated in Event."""

    rel_type: str = "PARTICIPATED_IN"
    role: str = ""


class MentionedInCreate(RelationshipBase):
    """Any entity mentioned in Document."""

    rel_type: str = "MENTIONED_IN"
    context: str = ""


class SubsidiaryOfCreate(RelationshipBase):
    """Organization subsidiary of Organization."""

    rel_type: str = "SUBSIDIARY_OF"
    ownership_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    since: str = ""


class AssociatedWithCreate(RelationshipBase):
    """Any entity associated with any entity (generic link)."""

    rel_type: str = "ASSOCIATED_WITH"
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class GenericRelationshipCreate(BaseModel):
    """Generic relationship creation that accepts any type."""

    source_id: str
    target_id: str
    source_label: str
    target_label: str
    rel_type: str
    properties: dict = Field(default_factory=dict)


class RelationshipOut(BaseModel):
    """Relationship output model."""

    source_id: str
    target_id: str
    source_label: str = ""
    target_label: str = ""
    rel_type: str
    properties: dict = Field(default_factory=dict)


# All valid relationship types and their allowed source→target labels
RELATIONSHIP_RULES: dict[str, list[tuple[list[str], list[str]]]] = {
    "OWNS": [(["Person", "Organization"], ["Account", "Property", "Organization"])],
    "DIRECTS": [(["Person"], ["Organization"])],
    "EMPLOYED_BY": [(["Person"], ["Organization"])],
    "TRANSFERRED_TO": [(["Account"], ["Account"])],
    "LOCATED_AT": [(["Person", "Organization"], ["Address"])],
    "CONTACTED": [(["Person"], ["Person"])],
    "RELATED_TO": [(["Person"], ["Person"])],
    "PARTICIPATED_IN": [(["Person", "Organization"], ["Event"])],
    "MENTIONED_IN": [(["Person", "Organization", "Account", "Property", "Event"], ["Document"])],
    "SUBSIDIARY_OF": [(["Organization"], ["Organization"])],
    "ASSOCIATED_WITH": [
        (
            ["Person", "Organization", "Account", "Property", "Event", "Document", "Address"],
            ["Person", "Organization", "Account", "Property", "Event", "Document", "Address"],
        )
    ],
}

VALID_REL_TYPES = list(RELATIONSHIP_RULES.keys())
