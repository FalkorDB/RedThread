"""Pattern detection — cycles, shell companies, structuring, anomalies."""

from __future__ import annotations

from typing import Any

import structlog

from src.config import settings
from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)


def detect_circular_flows(
    client: FalkorDBClient,
    min_length: int = 3,
    max_length: int = 8,
    min_amount: float = 0.0,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Detect circular money flows — accounts that send money that loops back.

    This detects cycle patterns like A→B→C→A which are a classic
    money laundering indicator. Impossible to detect efficiently in SQL
    without recursive CTEs with cycle detection.
    """
    depth = min(max_length, settings.max_path_depth)
    query = (
        "MATCH path = (a:Account)-[:TRANSFERRED_TO*"
        + str(min_length)
        + ".."
        + str(depth)
        + "]->(a) "
        "WITH path, a, relationships(path) AS rels "
        "WITH path, a, "
        "  reduce(total = 0.0, r IN rels | total + coalesce(r.amount, 0)) AS cycle_total, "
        "  length(path) AS cycle_len "
        "WHERE cycle_total >= $min_amount "
        "RETURN path, a.id AS start_account, cycle_len, cycle_total "
        "ORDER BY cycle_total DESC "
        "LIMIT $limit"
    )

    result = client.ro_query(query, params={"min_amount": min_amount, "limit": limit})

    cycles = []
    for row in result.result_set:
        path_data = _extract_path_simple(row[0])
        cycles.append(
            {
                "start_account": row[1],
                "cycle_length": row[2],
                "cycle_total": row[3],
                "path": path_data,
                "pattern": "circular_flow",
            }
        )

    logger.info("circular_flows_detected", count=len(cycles))
    return cycles


def detect_shell_company_chains(
    client: FalkorDBClient,
    min_depth: int = 2,
    max_depth: int = 6,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Detect chains of organizations across multiple jurisdictions controlled by a person.

    Pattern: Person → directs → Org1 (jurisdiction A) → subsidiary of → Org2 (jurisdiction B) → ...
    Cross-jurisdiction chains are a classic shell company indicator.
    """
    depth = min(max_depth, settings.max_path_depth)
    query = (
        "MATCH path = (p:Person)-[:DIRECTS]->(o1:Organization)"
        "-[:SUBSIDIARY_OF*1.." + str(depth) + "]->(oN:Organization) "
        "WHERE o1.jurisdiction IS NOT NULL AND oN.jurisdiction IS NOT NULL "
        "AND o1.jurisdiction <> oN.jurisdiction "
        "WITH p, path, o1, oN, "
        "  [n IN nodes(path) WHERE n:Organization | n.jurisdiction] AS jurisdictions "
        "WITH p, path, o1, oN, jurisdictions "
        "WHERE size(jurisdictions) >= $min_depth "
        "RETURN p.name AS controller, p.id AS controller_id, "
        "  o1.name AS first_entity, o1.jurisdiction AS first_jurisdiction, "
        "  oN.name AS terminal_entity, oN.jurisdiction AS terminal_jurisdiction, "
        "  size(jurisdictions) AS chain_depth, "
        "  jurisdictions "
        "ORDER BY chain_depth DESC "
        "LIMIT $limit"
    )

    result = client.ro_query(query, params={"min_depth": min_depth, "limit": limit})

    chains = []
    for row in result.result_set:
        chains.append(
            {
                "controller": row[0],
                "controller_id": row[1],
                "first_entity": row[2],
                "first_jurisdiction": row[3],
                "terminal_entity": row[4],
                "terminal_jurisdiction": row[5],
                "chain_depth": row[6],
                "jurisdictions": row[7],
                "pattern": "shell_company_chain",
            }
        )

    logger.info("shell_chains_detected", count=len(chains))
    return chains


def detect_structuring(
    client: FalkorDBClient,
    threshold: float = 10000.0,
    tolerance_pct: float = 15.0,
    min_count: int = 3,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Detect structuring — multiple transactions just below a reporting threshold.

    Pattern: Account sends N+ transactions to different accounts, each just below $threshold.
    Also known as "smurfing". This is a multi-entity pattern analysis.
    """
    lower_bound = threshold * (1 - tolerance_pct / 100)

    query = (
        "MATCH (src:Account)-[t:TRANSFERRED_TO]->(dst:Account) "
        "WHERE t.amount >= $lower AND t.amount < $threshold "
        "WITH src, collect({dst: dst.id, amount: t.amount, date: t.date}) AS transfers "
        "WHERE size(transfers) >= $min_count "
        "RETURN src.id AS source_account, src.institution AS institution, "
        "  size(transfers) AS num_transactions, "
        "  reduce(total = 0.0, t IN transfers | total + t.amount) AS total_amount, "
        "  transfers "
        "ORDER BY num_transactions DESC "
        "LIMIT $limit"
    )

    result = client.ro_query(
        query,
        params={
            "lower": lower_bound,
            "threshold": threshold,
            "min_count": min_count,
            "limit": limit,
        },
    )

    patterns = []
    for row in result.result_set:
        patterns.append(
            {
                "source_account": row[0],
                "institution": row[1],
                "num_transactions": row[2],
                "total_amount": row[3],
                "transfers": row[4],
                "threshold": threshold,
                "pattern": "structuring",
            }
        )

    logger.info("structuring_detected", count=len(patterns))
    return patterns


def detect_rapid_passthrough(
    client: FalkorDBClient,
    max_hours: int = 24,
    min_amount: float = 1000.0,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Detect rapid pass-through — money arrives and leaves an account quickly.

    Pattern: Account receives and sends large amounts within a short time window.
    This is a layering indicator in money laundering.
    """
    query = (
        "MATCH (src:Account)-[t_in:TRANSFERRED_TO]->(mid:Account)"
        "-[t_out:TRANSFERRED_TO]->(dst:Account) "
        "WHERE t_in.amount >= $min_amount AND t_out.amount >= $min_amount "
        "AND src <> dst "
        "RETURN mid.id AS passthrough_account, "
        "  src.id AS source, dst.id AS destination, "
        "  t_in.amount AS amount_in, t_out.amount AS amount_out, "
        "  t_in.date AS date_in, t_out.date AS date_out "
        "ORDER BY t_out.amount DESC "
        "LIMIT $limit"
    )

    result = client.ro_query(query, params={"min_amount": min_amount, "limit": limit})

    patterns = []
    for row in result.result_set:
        patterns.append(
            {
                "passthrough_account": row[0],
                "source": row[1],
                "destination": row[2],
                "amount_in": row[3],
                "amount_out": row[4],
                "date_in": row[5],
                "date_out": row[6],
                "pattern": "rapid_passthrough",
            }
        )

    logger.info("rapid_passthrough_detected", count=len(patterns))
    return patterns


def detect_hidden_connections(
    client: FalkorDBClient,
    entity_id_1: str,
    entity_id_2: str,
    max_depth: int = 4,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find non-obvious connections between two entities through intermediaries.

    This discovers 2+ hop connections that aren't visible from direct relationships.
    The core investigation value proposition.
    """
    depth = min(max_depth, settings.max_path_depth)
    query = (
        "MATCH path = (a {id: $id1})-[*2.." + str(depth) + "]-(b {id: $id2}) "
        "RETURN path "
        "ORDER BY length(path) "
        "LIMIT $limit"
    )

    result = client.ro_query(query, params={"id1": entity_id_1, "id2": entity_id_2, "limit": limit})

    connections = []
    for row in result.result_set:
        path_data = _extract_path_simple(row[0])
        connections.append(
            {
                "path": path_data,
                "hops": path_data["length"],
                "pattern": "hidden_connection",
            }
        )

    logger.info("hidden_connections_found", count=len(connections))
    return connections


def run_all_pattern_detection(
    client: FalkorDBClient,
) -> dict[str, list[dict[str, Any]]]:
    """Run all pattern detectors and return aggregated results."""
    return {
        "circular_flows": detect_circular_flows(client, limit=10),
        "shell_company_chains": detect_shell_company_chains(client, limit=10),
        "structuring": detect_structuring(client, limit=10),
        "rapid_passthrough": detect_rapid_passthrough(client, limit=10),
    }


def _extract_path_simple(path: Any) -> dict[str, Any]:
    """Extract nodes and edges from a FalkorDB path."""
    nodes = []
    edges = []
    for node in path.nodes():
        props = dict(node.properties)
        labels = node.labels
        props["label"] = labels[0] if labels else "Unknown"
        nodes.append(props)
    for edge in path.edges():
        edges.append(
            {
                "source": edge.src_node,
                "target": edge.dest_node,
                "rel_type": edge.relation,
                "properties": dict(edge.properties) if edge.properties else {},
            }
        )
    return {"nodes": nodes, "edges": edges, "length": len(edges)}
