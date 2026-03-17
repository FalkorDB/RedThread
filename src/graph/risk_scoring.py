"""Risk score computation — propagation through ownership and control chains."""

from __future__ import annotations

from typing import Any

import structlog

from src.database.falkordb_client import FalkorDBClient

logger = structlog.get_logger(__name__)

# Base risk factors for entity attributes
JURISDICTION_RISK: dict[str, float] = {
    "panama": 80,
    "cayman islands": 75,
    "british virgin islands": 75,
    "seychelles": 70,
    "belize": 65,
    "vanuatu": 65,
    "cyprus": 40,
    "malta": 35,
    "luxembourg": 25,
    "switzerland": 20,
    "singapore": 15,
    "united states": 10,
    "united kingdom": 10,
    "germany": 5,
    "france": 5,
}

ORG_TYPE_RISK: dict[str, float] = {
    "trust": 30,
    "foundation": 25,
    "shell": 50,
    "company": 10,
    "ngo": 5,
    "government": 0,
}


def compute_entity_risk(
    client: FalkorDBClient,
    entity_id: str,
    depth: int = 3,
) -> dict[str, Any]:
    """Compute risk score for an entity by aggregating risk through its network.

    The risk score propagates through ownership and control relationships,
    with diminishing weight at greater distances. This requires multi-hop
    traversal with aggregation — a natural graph computation.
    """
    # Get direct entity info
    query = "MATCH (n {id: $id}) RETURN n, labels(n) AS lbls"
    result = client.ro_query(query, params={"id": entity_id})
    if not result.result_set:
        return {"entity_id": entity_id, "risk_score": 0, "factors": []}

    node = result.result_set[0][0]
    labels = result.result_set[0][1]
    props = dict(node.properties)
    label = labels[0] if labels else "Unknown"

    factors: list[dict[str, Any]] = []
    base_risk = 0.0

    # Factor 1: Jurisdiction risk (for organizations)
    if label == "Organization":
        jurisdiction = (props.get("jurisdiction") or "").lower()
        if jurisdiction in JURISDICTION_RISK:
            j_risk = JURISDICTION_RISK[jurisdiction]
            factors.append(
                {
                    "factor": "jurisdiction",
                    "detail": jurisdiction,
                    "score": j_risk,
                }
            )
            base_risk += j_risk

        org_type = (props.get("org_type") or "").lower()
        if org_type in ORG_TYPE_RISK:
            t_risk = ORG_TYPE_RISK[org_type]
            factors.append(
                {
                    "factor": "org_type",
                    "detail": org_type,
                    "score": t_risk,
                }
            )
            base_risk += t_risk

    # Factor 2: Connected high-risk entities (risk propagation through graph)
    prop_query = (
        "MATCH (center {id: $id})-[:OWNS|DIRECTS|SUBSIDIARY_OF|EMPLOYED_BY*1.."
        + str(depth)
        + "]-(connected) "
        "WHERE connected.risk_score > 0 AND connected.id <> $id "
        "WITH connected, labels(connected) AS lbls, "
        "  length(shortestPath((center)-[*]-(connected))) AS dist "
        "WHERE center.id = $id "
        "RETURN connected.id, connected.name, lbls, connected.risk_score, dist "
        "ORDER BY connected.risk_score DESC "
        "LIMIT 20"
    )
    try:
        prop_result = client.ro_query(prop_query, params={"id": entity_id})
        propagated_risk = 0.0
        for row in prop_result.result_set:
            c_id, c_name, c_lbls, c_risk, dist = row
            # Risk diminishes with distance: score / (2^distance)
            weight = c_risk / (2**dist)
            propagated_risk += weight
            factors.append(
                {
                    "factor": "connected_risk",
                    "detail": f"{c_name} ({c_lbls[0] if c_lbls else 'Unknown'}) at {dist} hops",
                    "score": round(weight, 2),
                }
            )
    except Exception as e:
        logger.warning("risk_propagation_failed", entity=entity_id, error=str(e))
        propagated_risk = 0.0

    # Factor 3: Transaction patterns
    try:
        tx_query = (
            "MATCH (a {id: $id})-[:OWNS]->(:Account)-[t:TRANSFERRED_TO]->(dst:Account) "
            "WITH count(t) AS tx_count, sum(t.amount) AS total_out "
            "RETURN tx_count, total_out"
        )
        tx_result = client.ro_query(tx_query, params={"id": entity_id})
        if tx_result.result_set:
            tx_count = tx_result.result_set[0][0] or 0
            total_out = tx_result.result_set[0][1] or 0
            if tx_count > 10:
                tx_risk = min(tx_count * 2, 30)
                factors.append(
                    {
                        "factor": "high_transaction_volume",
                        "detail": f"{tx_count} outgoing transactions totaling {total_out}",
                        "score": tx_risk,
                    }
                )
                base_risk += tx_risk
    except Exception:
        pass

    total_risk = min(base_risk + propagated_risk, 100.0)
    risk_data = {
        "entity_id": entity_id,
        "label": label,
        "risk_score": round(total_risk, 2),
        "base_risk": round(base_risk, 2),
        "propagated_risk": round(propagated_risk, 2),
        "factors": factors,
    }

    # Update the entity's risk_score in the graph
    try:
        update_query = "MATCH (n {id: $id}) SET n.risk_score = $risk"
        client.query(update_query, params={"id": entity_id, "risk": round(total_risk, 2)})
    except Exception:
        pass

    logger.info("risk_computed", entity=entity_id, risk=total_risk)
    return risk_data


def compute_network_risk(
    client: FalkorDBClient,
    entity_ids: list[str],
) -> list[dict[str, Any]]:
    """Compute risk scores for multiple entities."""
    return [compute_entity_risk(client, eid) for eid in entity_ids]


def get_highest_risk_entities(
    client: FalkorDBClient,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get entities with the highest risk scores."""
    query = (
        "MATCH (n) WHERE n.risk_score > 0 "
        "RETURN n, labels(n) AS lbls "
        "ORDER BY n.risk_score DESC "
        "LIMIT $limit"
    )
    result = client.ro_query(query, params={"limit": limit})

    entities = []
    for row in result.result_set:
        props = dict(row[0].properties)
        props["label"] = row[1][0] if row[1] else "Unknown"
        entities.append(props)
    return entities
