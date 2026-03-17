"""Tests for Redis/FalkorDB error handling in the API layer.

Verifies that query timeouts return 504, connection errors return 503,
and other Redis errors return 502 instead of generic 500.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError as RedisResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError
from starlette.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from src.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestQueryTimeoutHandling:
    """Query timeouts should return 504, not 500."""

    def test_query_timeout_returns_504(self, client: TestClient):
        with patch(
            "src.graph.analytics.graph_summary",
            side_effect=RedisResponseError("Query timed out"),
        ):
            resp = client.get("/api/analysis/stats")
            assert resp.status_code == 504
            assert "timed out" in resp.json()["error"].lower()

    def test_other_redis_error_returns_502(self, client: TestClient):
        with patch(
            "src.graph.analytics.graph_summary",
            side_effect=RedisResponseError("Unknown index"),
        ):
            resp = client.get("/api/analysis/stats")
            assert resp.status_code == 502
            assert "Graph query error" in resp.json()["error"]


class TestConnectionErrorHandling:
    """Connection errors should return 503, not 500."""

    def test_connection_error_returns_503(self, client: TestClient):
        with patch(
            "src.graph.analytics.graph_summary",
            side_effect=RedisConnectionError("Connection refused"),
        ):
            resp = client.get("/api/analysis/stats")
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["error"].lower()

    def test_timeout_error_returns_503(self, client: TestClient):
        with patch(
            "src.graph.analytics.graph_summary",
            side_effect=RedisTimeoutError("Connection timed out"),
        ):
            resp = client.get("/api/analysis/stats")
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["error"].lower()
