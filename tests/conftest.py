"""Pytest fixtures and configuration."""

from __future__ import annotations

import os

import pytest

# Set test configuration before importing app modules
os.environ["FALKORDB_PORT"] = os.environ.get("FALKORDB_PORT", "6380")
os.environ["FALKORDB_GRAPH_NAME"] = "redthread_test"
os.environ["SQLITE_DB_PATH"] = "/tmp/redthread_test.db"


@pytest.fixture(scope="session")
def falkordb_client():
    """Get a FalkorDB client connected to the test graph."""
    from src.database.falkordb_client import FalkorDBClient
    from src.database.schema import setup_schema

    client = FalkorDBClient(
        host=os.environ.get("FALKORDB_HOST", "localhost"),
        port=int(os.environ["FALKORDB_PORT"]),
        graph_name="redthread_test",
    )
    try:
        client.connect()
        client.delete_graph()
        client.connect()
        setup_schema(client)
    except Exception:
        pytest.skip("FalkorDB not available")

    yield client

    # Cleanup
    try:
        client.delete_graph()
    except Exception:
        pass
    client.close()


@pytest.fixture
def clean_graph(falkordb_client):
    """Provide a clean graph for each test."""
    falkordb_client.delete_graph()
    falkordb_client.connect()
    from src.database.schema import setup_schema

    setup_schema(falkordb_client)
    return falkordb_client


@pytest.fixture(scope="session")
def test_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient

    from src.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded_graph(clean_graph):
    """A graph pre-seeded with test data."""
    from src.graph.queries import create_entity, create_relationship

    client = clean_graph

    # Create test entities
    create_entity(
        client,
        "Person",
        {"id": "test-p1", "name": "John Doe", "nationality": "US", "risk_score": 60},
    )
    create_entity(
        client,
        "Person",
        {"id": "test-p2", "name": "Jane Smith", "nationality": "UK", "risk_score": 20},
    )
    create_entity(
        client,
        "Organization",
        {
            "id": "test-o1",
            "name": "Shell Corp",
            "org_type": "company",
            "jurisdiction": "Panama",
            "risk_score": 75,
        },
    )
    create_entity(
        client,
        "Organization",
        {
            "id": "test-o2",
            "name": "Real Corp",
            "org_type": "company",
            "jurisdiction": "United States",
        },
    )
    create_entity(
        client, "Account", {"id": "test-a1", "account_number": "ACC-001", "institution": "Bank A"}
    )
    create_entity(
        client, "Account", {"id": "test-a2", "account_number": "ACC-002", "institution": "Bank B"}
    )
    create_entity(
        client, "Account", {"id": "test-a3", "account_number": "ACC-003", "institution": "Bank C"}
    )
    create_entity(
        client,
        "Address",
        {"id": "test-addr1", "full_address": "123 Main St, Panama City", "country": "Panama"},
    )

    # Create relationships
    create_relationship(
        client, "Person", "test-p1", "Organization", "test-o1", "DIRECTS", {"role": "director"}
    )
    create_relationship(
        client, "Person", "test-p2", "Organization", "test-o2", "EMPLOYED_BY", {"position": "CEO"}
    )
    create_relationship(client, "Organization", "test-o1", "Account", "test-a1", "OWNS", {})
    create_relationship(client, "Organization", "test-o2", "Account", "test-a2", "OWNS", {})
    create_relationship(
        client,
        "Account",
        "test-a1",
        "Account",
        "test-a2",
        "TRANSFERRED_TO",
        {"amount": 50000, "date": "2024-01-15"},
    )
    create_relationship(
        client,
        "Account",
        "test-a2",
        "Account",
        "test-a3",
        "TRANSFERRED_TO",
        {"amount": 45000, "date": "2024-01-16"},
    )
    create_relationship(
        client,
        "Account",
        "test-a3",
        "Account",
        "test-a1",
        "TRANSFERRED_TO",
        {"amount": 40000, "date": "2024-01-17"},
    )
    create_relationship(
        client, "Organization", "test-o1", "Address", "test-addr1", "LOCATED_AT", {}
    )
    create_relationship(
        client,
        "Person",
        "test-p1",
        "Person",
        "test-p2",
        "CONTACTED",
        {"method": "phone", "date": "2024-01-10"},
    )
    create_relationship(
        client,
        "Organization",
        "test-o1",
        "Organization",
        "test-o2",
        "SUBSIDIARY_OF",
        {"ownership_pct": 60},
    )

    return client
