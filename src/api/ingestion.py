"""Data import API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from src.database.falkordb_client import db
from src.ingestion.csv_importer import import_entities_csv, import_relationships_csv
from src.ingestion.json_importer import import_json
from src.ingestion.validators import VALID_LABELS, VALID_REL_TYPES

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/csv/entities")
async def import_csv_entities(
    file: UploadFile = File(...),
    label: str = Query(..., description="Entity label (Person, Organization, etc.)"),
) -> dict[str, Any]:
    """Import entities from a CSV file."""
    if label not in VALID_LABELS:
        raise HTTPException(
            400,
            f"Invalid entity label: '{label}'. Must be one of: {sorted(VALID_LABELS)}",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "File must be a CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    return import_entities_csv(db, text, label)


@router.post("/csv/relationships")
async def import_csv_relationships(
    file: UploadFile = File(...),
    rel_type: str = Query(..., description="Relationship type"),
) -> dict[str, Any]:
    """Import relationships from a CSV file."""
    if rel_type not in VALID_REL_TYPES:
        raise HTTPException(
            400,
            f"Invalid relationship type: '{rel_type}'. Must be one of: {sorted(VALID_REL_TYPES)}",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "File must be a CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    return import_relationships_csv(db, text, rel_type)


@router.post("/json")
async def import_json_data(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Import entities and relationships from a JSON file."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(400, "File must be a JSON")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "File must be UTF-8 encoded") from exc

    result = import_json(db, text)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/json/inline")
def import_json_inline(data: dict[str, Any]) -> dict[str, Any]:
    """Import entities and relationships from inline JSON."""
    import json

    result = import_json(db, json.dumps(data))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result
