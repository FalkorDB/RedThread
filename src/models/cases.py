"""Pydantic models for investigation/case management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InvestigationCreate(BaseModel):
    """Create a new investigation."""

    name: str = Field(..., min_length=1, max_length=300)
    description: str = ""


class InvestigationUpdate(BaseModel):
    """Update an investigation."""

    name: str | None = None
    description: str | None = None
    status: str | None = Field(None, pattern="^(active|archived|closed)$")


class Investigation(BaseModel):
    """Investigation output model."""

    id: str
    name: str
    description: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    entity_count: int = 0


class InvestigationEntity(BaseModel):
    """An entity pinned to an investigation."""

    entity_id: str
    entity_label: str
    pinned: bool = False
    notes: str = ""
    added_at: str = ""


class SnapshotCreate(BaseModel):
    """Create an investigation snapshot."""

    name: str = Field(..., min_length=1, max_length=200)
    graph_state: str
    viewport: str = "{}"


class Snapshot(BaseModel):
    """Snapshot output model."""

    id: str
    investigation_id: str
    name: str
    graph_state: str
    viewport: str = "{}"
    created_at: str = ""


class TagCreate(BaseModel):
    """Create a tag."""

    name: str = Field(..., min_length=1, max_length=50)
    color: str = "#6366f1"


class Tag(BaseModel):
    """Tag output model."""

    id: str
    name: str
    color: str = "#6366f1"
