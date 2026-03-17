"""Natural language query API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.database.falkordb_client import db
from src.graph import nlq

router = APIRouter(prefix="/api/nlq", tags=["natural-language-query"])


class NLQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about the graph")


@router.post("/query")
def nl_query(request: NLQueryRequest) -> dict[str, Any]:
    """Translate a natural language question to Cypher and execute it."""
    return nlq.execute_nl_query(db, request.question)


@router.post("/translate")
def nl_translate(request: NLQueryRequest) -> dict[str, Any]:
    """Translate a natural language question to Cypher without executing."""
    return nlq.translate_to_cypher(request.question)


@router.get("/examples")
def get_examples() -> list[str]:
    """Get example natural language queries."""
    return nlq.EXAMPLE_QUERIES
