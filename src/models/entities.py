"""Pydantic models for graph entities."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EntityBase(BaseModel):
    """Base model for all graph entities."""

    id: str = Field(default="", description="Unique identifier")
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class PersonCreate(BaseModel):
    """Create a Person node."""

    name: str = Field(..., min_length=1, max_length=500)
    aliases: list[str] = Field(default_factory=list)
    dob: str = ""
    nationality: str = ""
    role: str = ""
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""


class Person(EntityBase):
    name: str
    aliases: list[str] = Field(default_factory=list)
    dob: str = ""
    nationality: str = ""
    role: str = ""
    label: str = "Person"


class OrganizationCreate(BaseModel):
    """Create an Organization node."""

    name: str = Field(..., min_length=1, max_length=500)
    org_type: str = Field(default="company", description="company|trust|foundation|government|ngo")
    jurisdiction: str = ""
    registration_number: str = ""
    status: str = "active"
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""


class Organization(EntityBase):
    name: str
    org_type: str = "company"
    jurisdiction: str = ""
    registration_number: str = ""
    status: str = "active"
    label: str = "Organization"


class AccountCreate(BaseModel):
    """Create an Account node."""

    account_number: str = Field(..., min_length=1, max_length=200)
    account_type: str = Field(default="bank", description="bank|crypto|brokerage|cash")
    institution: str = ""
    currency: str = "USD"
    status: str = "active"
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""


class Account(EntityBase):
    account_number: str
    account_type: str = "bank"
    institution: str = ""
    currency: str = "USD"
    status: str = "active"
    label: str = "Account"


class PropertyCreate(BaseModel):
    """Create a Property node."""

    property_type: str = Field(
        default="real_estate", description="real_estate|vehicle|yacht|aircraft|art|other"
    )
    description: str = ""
    value: float = 0.0
    currency: str = "USD"
    location: str = ""
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""


class Property(EntityBase):
    property_type: str = "real_estate"
    description: str = ""
    value: float = 0.0
    currency: str = "USD"
    location: str = ""
    label: str = "Property"


class EventCreate(BaseModel):
    """Create an Event node."""

    event_type: str = Field(
        ..., description="transaction|meeting|communication|travel|filing|arrest|sanction"
    )
    date: str = ""
    description: str = ""
    amount: float = 0.0
    currency: str = "USD"
    location: str = ""
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""


class Event(EntityBase):
    event_type: str
    date: str = ""
    description: str = ""
    amount: float = 0.0
    currency: str = "USD"
    location: str = ""
    label: str = "Event"


class DocumentCreate(BaseModel):
    """Create a Document node."""

    doc_type: str = Field(
        default="report", description="contract|filing|report|communication|court_order"
    )
    date: str = ""
    source: str = ""
    title: str = ""
    summary: str = ""
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: str = ""


class Document(EntityBase):
    doc_type: str = "report"
    date: str = ""
    source: str = ""
    title: str = ""
    summary: str = ""
    label: str = "Document"


class AddressCreate(BaseModel):
    """Create an Address node."""

    full_address: str = Field(..., min_length=1)
    city: str = ""
    country: str = ""
    postal_code: str = ""
    lat: float = 0.0
    lon: float = 0.0
    notes: str = ""


class Address(EntityBase):
    full_address: str
    city: str = ""
    country: str = ""
    postal_code: str = ""
    lat: float = 0.0
    lon: float = 0.0
    label: str = "Address"


# Union type for any entity
ENTITY_LABELS = ["Person", "Organization", "Account", "Property", "Event", "Document", "Address"]

CREATE_MODEL_MAP: dict[str, type[BaseModel]] = {
    "Person": PersonCreate,
    "Organization": OrganizationCreate,
    "Account": AccountCreate,
    "Property": PropertyCreate,
    "Event": EventCreate,
    "Document": DocumentCreate,
    "Address": AddressCreate,
}

ENTITY_MODEL_MAP: dict[str, type[EntityBase]] = {
    "Person": Person,
    "Organization": Organization,
    "Account": Account,
    "Property": Property,
    "Event": Event,
    "Document": Document,
    "Address": Address,
}


def entity_from_node(label: str, properties: dict[str, Any]) -> EntityBase:
    """Create an entity model from a graph node's properties."""
    model_class = ENTITY_MODEL_MAP.get(label)
    if not model_class:
        raise ValueError(f"Unknown entity label: {label}")

    # Handle aliases stored as string
    if label == "Person" and isinstance(properties.get("aliases"), str):
        import json

        try:
            properties["aliases"] = json.loads(properties["aliases"])
        except (json.JSONDecodeError, TypeError):
            properties["aliases"] = []

    return model_class(**{k: v for k, v in properties.items() if v is not None})
