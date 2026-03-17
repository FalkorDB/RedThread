"""Natural Language → Cypher query translation using LLM."""

from __future__ import annotations

import re
from typing import Any

import structlog

from src.config import settings
from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)

GRAPH_SCHEMA_PROMPT = """You are a Cypher query expert for a FalkorDB graph database used in a financial investigation platform called RedThread.

## Graph Schema

### Node Types and Properties:
- **Person**: id, name, nationality, date_of_birth, role, risk_score, aliases (JSON array string)
- **Organization**: id, name, jurisdiction, org_type (company|trust|fund|bank|government|ngo|shell_company), registration_number, risk_score
- **Account**: id, account_number, institution, account_type (bank|crypto|investment|trust), currency, status
- **Property**: id, property_type (real_estate|vehicle|vessel|aircraft|art|jewelry), description, estimated_value, location
- **Event**: id, event_type (meeting|transaction|filing|arrest|sanction|travel), date, description, location
- **Document**: id, doc_type (contract|filing|report|communication|bank_statement|passport|incorporation), date, title, source
- **Address**: id, street, city, country, postal_code, full_address

### Relationship Types and Properties:
- **OWNS**: Person/Organization → Account/Property/Organization. Props: share_pct, since, until, valid_from, valid_to
- **DIRECTS**: Person → Organization. Props: role, since, until, valid_from, valid_to
- **EMPLOYED_BY**: Person → Organization. Props: position, since, until, valid_from, valid_to
- **TRANSFERRED_TO**: Account → Account. Props: amount, currency, date, reference, valid_from, valid_to
- **LOCATED_AT**: Person/Organization → Address. Props: addr_type (registered|residential|operational), since, valid_from, valid_to
- **CONTACTED**: Person → Person. Props: method, date, duration, valid_from, valid_to
- **RELATED_TO**: Person → Person. Props: relationship_type (family|business|associate|romantic), since, valid_from, valid_to
- **PARTICIPATED_IN**: Person/Organization → Event. Props: role, valid_from, valid_to
- **MENTIONED_IN**: Any → Document. Props: context, valid_from, valid_to
- **SUBSIDIARY_OF**: Organization → Organization. Props: ownership_pct, since, valid_from, valid_to
- **ASSOCIATED_WITH**: Any → Any. Props: evidence, confidence, valid_from, valid_to

## Rules:
1. Generate ONLY read-only Cypher queries (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT). Never use CREATE, DELETE, SET, MERGE, REMOVE, DROP.
2. Always use parameterized queries where possible, but since this is a direct translation, inline string values are acceptable.
3. Use FalkorDB-compatible Cypher syntax. FalkorDB does not support OPTIONAL MATCH, UNWIND, or CALL procedures.
4. For shortestPath, use: RETURN shortestPath((a)-[*1..N]->(b)) — must be directed and in RETURN clause.
5. Always include a LIMIT clause (default LIMIT 50).
6. Return meaningful properties, not just node objects when possible.
7. For money amounts, the property is `amount` on TRANSFERRED_TO relationships.
8. For temporal filtering, use valid_from and valid_to properties.

## Output Format:
Return ONLY the Cypher query. No explanation, no markdown, no backticks. Just the raw Cypher query.
"""


def translate_to_cypher(question: str) -> dict[str, Any]:
    """Translate a natural language question to a Cypher query using an LLM.

    Returns the generated Cypher query and metadata.
    Requires OPENAI_API_KEY or compatible API configuration.
    """
    if not settings.llm_api_key:
        return {
            "error": "LLM not configured. Set LLM_API_KEY environment variable.",
            "query": None,
            "question": question,
        }

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
        )

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": GRAPH_SCHEMA_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=1000,
        )

        raw_query = response.choices[0].message.content.strip()

        # Clean up: remove markdown code fences if present
        raw_query = re.sub(r"^```(?:cypher)?\s*", "", raw_query)
        raw_query = re.sub(r"\s*```$", "", raw_query)
        raw_query = raw_query.strip()

        # Safety check: reject write operations
        if _is_write_query(raw_query):
            return {
                "error": "Generated query contains write operations — rejected for safety.",
                "query": raw_query,
                "question": question,
                "safe": False,
            }

        return {
            "query": raw_query,
            "question": question,
            "model": settings.llm_model,
            "safe": True,
        }

    except ImportError:
        return {
            "error": "openai package not installed. Run: pip install openai",
            "query": None,
            "question": question,
        }
    except Exception as e:
        logger.error("llm_translation_failed", error=str(e), question=question)
        return {
            "error": f"LLM translation failed: {str(e)}",
            "query": None,
            "question": question,
        }


def execute_nl_query(
    client: FalkorDBClient,
    question: str,
) -> dict[str, Any]:
    """Translate a natural language question to Cypher, execute it, and return results."""
    translation = translate_to_cypher(question)

    if translation.get("error") or not translation.get("query"):
        return translation

    query = translation["query"]

    # Double-check safety
    if _is_write_query(query):
        return {
            "error": "Query rejected: contains write operations.",
            "query": query,
            "question": question,
            "safe": False,
        }

    try:
        result = client.ro_query(query)
        rows = _format_result(result)
        return {
            "question": question,
            "query": query,
            "model": translation.get("model"),
            "results": rows,
            "count": len(rows),
            "safe": True,
        }
    except Exception as e:
        logger.error("nl_query_execution_failed", error=str(e), query=query)
        return {
            "question": question,
            "query": query,
            "error": f"Query execution failed: {str(e)}",
            "safe": True,
        }


def _is_write_query(query: str) -> bool:
    """Check if a Cypher query contains any write operations."""
    write_keywords = [
        r"\bCREATE\b",
        r"\bDELETE\b",
        r"\bDETACH\b",
        r"\bSET\b",
        r"\bMERGE\b",
        r"\bREMOVE\b",
        r"\bDROP\b",
        r"\bCALL\b",
    ]
    upper = query.upper()
    for pattern in write_keywords:
        if re.search(pattern, upper):
            # "SET" is tricky — could be in a RETURN alias. Only flag if before RETURN
            if pattern == r"\bSET\b":
                return_pos = upper.find("RETURN")
                set_pos = upper.find("SET")
                if return_pos != -1 and set_pos > return_pos:
                    continue
            return True
    return False


def _format_result(result: Any) -> list[dict[str, Any]]:
    """Format FalkorDB query results into serializable dicts."""
    rows = []
    header = result.header if hasattr(result, "header") else []

    for record in result.result_set:
        row: dict[str, Any] = {}
        for i, value in enumerate(record):
            col_name = header[i] if i < len(header) else f"col_{i}"
            # Handle node objects
            if hasattr(value, "properties"):
                props = dict(value.properties)
                if hasattr(value, "labels") and value.labels:
                    props["_label"] = value.labels[0]
                row[col_name] = props
            # Handle path objects
            elif hasattr(value, "nodes"):
                row[col_name] = {
                    "nodes": [dict(n.properties) for n in value.nodes()],
                    "length": len(value.edges()),
                }
            # Handle edge objects
            elif hasattr(value, "relation"):
                row[col_name] = {
                    "rel_type": value.relation,
                    "source": value.src_node,
                    "target": value.dest_node,
                    "properties": dict(value.properties) if value.properties else {},
                }
            else:
                row[col_name] = value
        rows.append(row)
    return rows


# Pre-built example queries for the UI
EXAMPLE_QUERIES = [
    "Show me all persons connected to Golden Gate Holdings",
    "Find all money transfers over $1,000,000",
    "Who directs organizations in the BVI?",
    "Show the shortest path between Viktor Kovacs and any account in Switzerland",
    "Find all organizations that are subsidiaries of another organization",
    "List all persons with nationality 'Hungarian'",
    "Show all accounts at Zurich Private Bank",
    "Find persons who are connected to more than 3 organizations",
    "List all transfers from Golden Gate accounts",
    "Who owns property worth more than $5,000,000?",
]
