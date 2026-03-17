"""Integration tests for API endpoints."""

from __future__ import annotations


class TestAPIEntities:
    def test_health_check(self, test_client):
        res = test_client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["healthy", "degraded"]

    def test_create_and_get_person(self, test_client):
        res = test_client.post(
            "/api/entities/person",
            json={
                "name": "API Test Person",
                "nationality": "France",
                "risk_score": 35,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "API Test Person"
        entity_id = data["id"]

        res2 = test_client.get(f"/api/entities/{entity_id}")
        assert res2.status_code == 200
        assert res2.json()["name"] == "API Test Person"

    def test_search_entities(self, test_client):
        # Create entity first
        test_client.post("/api/entities/person", json={"name": "Searchable Person"})
        res = test_client.get("/api/entities/?q=Searchable")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0

    def test_entity_not_found(self, test_client):
        res = test_client.get("/api/entities/nonexistent-id")
        assert res.status_code == 404

    def test_list_entities_by_label(self, test_client):
        res = test_client.get("/api/entities/?label=Person")
        assert res.status_code == 200
        data = res.json()
        assert "entities" in data


class TestAPIAnalysis:
    def test_graph_stats(self, test_client):
        res = test_client.get("/api/analysis/stats")
        assert res.status_code == 200
        data = res.json()
        assert "total_nodes" in data

    def test_centrality(self, test_client):
        res = test_client.get("/api/analysis/centrality")
        assert res.status_code == 200

    def test_pattern_detection(self, test_client):
        res = test_client.get("/api/analysis/patterns")
        assert res.status_code == 200
        data = res.json()
        assert "circular_flows" in data

    def test_highest_risk(self, test_client):
        res = test_client.get("/api/analysis/risk")
        assert res.status_code == 200


class TestAPIInvestigations:
    def test_create_investigation(self, test_client):
        res = test_client.post(
            "/api/investigations/",
            json={
                "name": "Test Investigation",
                "description": "Testing the API",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Test Investigation"
        assert "id" in data

    def test_list_investigations(self, test_client):
        res = test_client.get("/api/investigations/")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
