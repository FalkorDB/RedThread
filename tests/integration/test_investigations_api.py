"""Tests for investigation/case management API endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(test_client: TestClient) -> TestClient:
    return test_client


def _create_inv(client: TestClient, name: str = "Test Case", desc: str = "Desc") -> dict[str, Any]:
    """Helper to create an investigation and return its JSON."""
    resp = client.post("/api/investigations/", json={"name": name, "description": desc})
    assert resp.status_code == 200
    return resp.json()


class TestInvestigationCRUD:
    """Create, read, update, delete investigations."""

    def test_create_investigation(self, client: TestClient):
        data = _create_inv(client)
        assert data["name"] == "Test Case"
        assert data["status"] == "active"
        assert "id" in data

    def test_list_investigations(self, client: TestClient):
        _create_inv(client, "Inv 1")
        _create_inv(client, "Inv 2")
        resp = client.get("/api/investigations/")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 2

    def test_list_investigations_with_status_filter(self, client: TestClient):
        _create_inv(client, "Active Inv")
        resp = client.get("/api/investigations/?status=active")
        assert resp.status_code == 200
        for item in resp.json():
            assert item["status"] == "active"

    def test_list_investigations_with_limit(self, client: TestClient):
        _create_inv(client, "A")
        _create_inv(client, "B")
        _create_inv(client, "C")
        resp = client.get("/api/investigations/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    def test_get_investigation(self, client: TestClient):
        inv = _create_inv(client)
        resp = client.get(f"/api/investigations/{inv['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == inv["id"]
        assert "entities" in resp.json()

    def test_get_investigation_not_found(self, client: TestClient):
        resp = client.get("/api/investigations/nonexistent")
        assert resp.status_code == 404

    def test_update_investigation_name(self, client: TestClient):
        inv = _create_inv(client)
        resp = client.put(f"/api/investigations/{inv['id']}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_update_investigation_status(self, client: TestClient):
        inv = _create_inv(client)
        resp = client.put(f"/api/investigations/{inv['id']}", json={"status": "closed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_update_investigation_not_found(self, client: TestClient):
        resp = client.put("/api/investigations/nonexistent", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_investigation(self, client: TestClient):
        inv = _create_inv(client)
        resp = client.delete(f"/api/investigations/{inv['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        # Verify it's gone
        resp2 = client.get(f"/api/investigations/{inv['id']}")
        assert resp2.status_code == 404


class TestInvestigationEntities:
    """Add/remove entities from investigations."""

    def test_add_entity_to_investigation(self, client: TestClient):
        inv = _create_inv(client)
        resp = client.post(
            f"/api/investigations/{inv['id']}/entities?entity_id=p-1&entity_label=Person"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "added"

    def test_add_entity_to_nonexistent_investigation(self, client: TestClient):
        resp = client.post(
            "/api/investigations/nonexistent/entities?entity_id=p-1&entity_label=Person"
        )
        assert resp.status_code == 404

    def test_investigation_includes_entities(self, client: TestClient):
        inv = _create_inv(client)
        client.post(f"/api/investigations/{inv['id']}/entities?entity_id=p-1&entity_label=Person")
        resp = client.get(f"/api/investigations/{inv['id']}")
        assert resp.status_code == 200
        entities = resp.json()["entities"]
        assert len(entities) == 1
        assert entities[0]["entity_id"] == "p-1"

    def test_remove_entity_from_investigation(self, client: TestClient):
        inv = _create_inv(client)
        client.post(f"/api/investigations/{inv['id']}/entities?entity_id=p-1&entity_label=Person")
        resp = client.delete(f"/api/investigations/{inv['id']}/entities/p-1")
        assert resp.status_code == 200
        # Verify removed
        inv_detail = client.get(f"/api/investigations/{inv['id']}").json()
        assert len(inv_detail["entities"]) == 0

    def test_entity_count_in_list(self, client: TestClient):
        inv = _create_inv(client)
        client.post(f"/api/investigations/{inv['id']}/entities?entity_id=p-1&entity_label=Person")
        client.post(f"/api/investigations/{inv['id']}/entities?entity_id=p-2&entity_label=Person")
        resp = client.get("/api/investigations/")
        items = resp.json()
        matching = [i for i in items if i["id"] == inv["id"]]
        assert matching[0]["entity_count"] == 2


class TestInvestigationTags:
    """Tag CRUD and entity tagging."""

    def test_create_tag(self, client: TestClient):
        import uuid

        tag_name = f"tag-{uuid.uuid4().hex[:8]}"
        resp = client.post("/api/investigations/tags", json={"name": tag_name, "color": "#ff0000"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == tag_name
        assert data["color"] == "#ff0000"
        assert "id" in data

    def test_list_tags(self, client: TestClient):
        import uuid

        client.post(
            "/api/investigations/tags",
            json={"name": f"alpha-{uuid.uuid4().hex[:8]}", "color": "#000"},
        )
        client.post(
            "/api/investigations/tags",
            json={"name": f"beta-{uuid.uuid4().hex[:8]}", "color": "#111"},
        )
        resp = client.get("/api/investigations/tags/all")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_tag_entity(self, client: TestClient):
        import uuid

        tag = client.post(
            "/api/investigations/tags",
            json={"name": f"flagged-{uuid.uuid4().hex[:8]}", "color": "#f00"},
        ).json()
        resp = client.post(f"/api/investigations/tags/p-1/{tag['id']}")
        assert resp.status_code == 200


class TestInvestigationSnapshots:
    """Snapshot management within investigations."""

    def test_create_snapshot(self, client: TestClient):
        inv = _create_inv(client)
        resp = client.post(
            f"/api/investigations/{inv['id']}/snapshots",
            json={"name": "snap-1", "graph_state": "{}", "viewport": "{}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "snap-1"

    def test_list_snapshots(self, client: TestClient):
        inv = _create_inv(client)
        client.post(
            f"/api/investigations/{inv['id']}/snapshots",
            json={"name": "s1", "graph_state": "{}", "viewport": "{}"},
        )
        client.post(
            f"/api/investigations/{inv['id']}/snapshots",
            json={"name": "s2", "graph_state": "{}", "viewport": "{}"},
        )
        resp = client.get(f"/api/investigations/{inv['id']}/snapshots")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_snapshots_with_limit(self, client: TestClient):
        inv = _create_inv(client)
        for i in range(3):
            client.post(
                f"/api/investigations/{inv['id']}/snapshots",
                json={"name": f"s{i}", "graph_state": "{}", "viewport": "{}"},
            )
        resp = client.get(f"/api/investigations/{inv['id']}/snapshots?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2
