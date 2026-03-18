"""Tests for tag management API endpoints."""

import pytest


@pytest.fixture()
def _clean_tags(test_client):
    """Remove all tags before a test."""
    tags = test_client.get("/api/investigations/tags/all").json()
    for tag in tags:
        test_client.delete(f"/api/investigations/tags/{tag['id']}")
    yield
    tags = test_client.get("/api/investigations/tags/all").json()
    for tag in tags:
        test_client.delete(f"/api/investigations/tags/{tag['id']}")


class TestTagCRUD:
    """Tag create / list / delete."""

    def test_create_tag(self, test_client, _clean_tags):
        resp = test_client.post(
            "/api/investigations/tags",
            json={"name": "Suspicious", "color": "#ff0000"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Suspicious"
        assert body["color"] == "#ff0000"
        assert "id" in body

    def test_list_tags(self, test_client, _clean_tags):
        test_client.post("/api/investigations/tags", json={"name": "Alpha"})
        test_client.post("/api/investigations/tags", json={"name": "Beta"})
        tags = test_client.get("/api/investigations/tags/all").json()
        names = [t["name"] for t in tags]
        assert "Alpha" in names
        assert "Beta" in names

    def test_create_duplicate_tag_returns_409(self, test_client, _clean_tags):
        test_client.post("/api/investigations/tags", json={"name": "Dup"})
        resp = test_client.post("/api/investigations/tags", json={"name": "Dup"})
        assert resp.status_code == 409

    def test_delete_tag(self, test_client, _clean_tags):
        tag = test_client.post("/api/investigations/tags", json={"name": "Temp"}).json()
        resp = test_client.delete(f"/api/investigations/tags/{tag['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        tags = test_client.get("/api/investigations/tags/all").json()
        assert all(t["id"] != tag["id"] for t in tags)

    def test_delete_nonexistent_tag_returns_404(self, test_client, _clean_tags):
        resp = test_client.delete("/api/investigations/tags/nonexistent")
        assert resp.status_code == 404


class TestEntityTagging:
    """Tag ↔ entity association."""

    @pytest.fixture()
    def _setup(self, test_client, _clean_tags):
        """Create one entity and one tag for tagging tests."""
        entity = test_client.post("/api/entities/person", json={"name": "Tag Target"}).json()
        tag = test_client.post(
            "/api/investigations/tags", json={"name": "VIP", "color": "#00ff00"}
        ).json()
        self.entity_id = entity["id"]
        self.tag_id = tag["id"]

    def test_tag_entity(self, test_client, _setup):
        resp = test_client.post(f"/api/investigations/tags/{self.entity_id}/{self.tag_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "tagged"

    def test_get_entity_tags(self, test_client, _setup):
        test_client.post(f"/api/investigations/tags/{self.entity_id}/{self.tag_id}")
        resp = test_client.get(f"/api/investigations/tags/entity/{self.entity_id}")
        assert resp.status_code == 200
        tags = resp.json()
        assert len(tags) >= 1
        assert any(t["name"] == "VIP" for t in tags)

    def test_untag_entity(self, test_client, _setup):
        test_client.post(f"/api/investigations/tags/{self.entity_id}/{self.tag_id}")
        resp = test_client.delete(f"/api/investigations/tags/{self.entity_id}/{self.tag_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "untagged"
        tags = test_client.get(f"/api/investigations/tags/entity/{self.entity_id}").json()
        assert all(t["id"] != self.tag_id for t in tags)

    def test_tag_nonexistent_tag_returns_404(self, test_client, _setup):
        resp = test_client.post(f"/api/investigations/tags/{self.entity_id}/nonexistent")
        assert resp.status_code == 404

    def test_get_entity_tags_empty(self, test_client, _setup):
        resp = test_client.get(f"/api/investigations/tags/entity/{self.entity_id}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_tag_entity_idempotent(self, test_client, _setup):
        """Tagging same entity twice should not duplicate."""
        test_client.post(f"/api/investigations/tags/{self.entity_id}/{self.tag_id}")
        test_client.post(f"/api/investigations/tags/{self.entity_id}/{self.tag_id}")
        tags = test_client.get(f"/api/investigations/tags/entity/{self.entity_id}").json()
        vip_count = sum(1 for t in tags if t["name"] == "VIP")
        assert vip_count == 1
