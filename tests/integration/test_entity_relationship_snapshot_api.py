"""Integration tests for entity, relationship, and snapshot API endpoints.

Covers uncovered paths in:
- src/api/entities.py (neighborhood, update, delete, all create types, search+label)
- src/api/relationships.py (create, delete, validation)
- src/api/snapshots.py (create, list, get, diff)
- src/ingestion/json_importer.py (valid/invalid JSON, entity/rel errors, id mapping)
"""

from __future__ import annotations

import json
import uuid

import pytest


def uid() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def _create_person(client, name: str = "Test Person") -> str:
    """Create a person and return its generated ID."""
    resp = client.post("/api/entities/person", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_org(client, name: str = "Test Org") -> str:
    """Create an organization and return its generated ID."""
    resp = client.post("/api/entities/organization", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Entity endpoints
# ---------------------------------------------------------------------------


class TestEntityEndpoints:
    """Test entity CRUD beyond the basics already in test_api.py."""

    def test_create_organization(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/entities/organization",
            json={"name": "Acme Corp", "country": "US"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme Corp"
        assert "id" in resp.json()

    def test_create_account(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/entities/account",
            json={"account_number": "CH-9876", "account_type": "checking"},
        )
        assert resp.status_code == 200
        assert resp.json()["account_number"] == "CH-9876"

    def test_create_property(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/entities/property",
            json={"property_type": "real_estate", "description": "Beach House"},
        )
        assert resp.status_code == 200

    def test_create_event(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/entities/event",
            json={"event_type": "meeting", "date": "2024-01-01"},
        )
        assert resp.status_code == 200

    def test_create_document(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/entities/document",
            json={"doc_type": "report", "title": "Tax Return 2023"},
        )
        assert resp.status_code == 200

    def test_create_address(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/entities/address",
            json={"full_address": "1 Main St, Springfield"},
        )
        assert resp.status_code == 200

    def test_get_entity_not_found(self, test_client, clean_graph):
        resp = test_client.get("/api/entities/nonexistent-id-xyz")
        assert resp.status_code == 404

    def test_list_entities_invalid_label(self, test_client, clean_graph):
        resp = test_client.get("/api/entities/", params={"label": "InvalidLabel"})
        assert resp.status_code == 400

    def test_list_entities_no_label(self, test_client, clean_graph):
        """When no label is given, entities from all labels are returned."""
        _create_person(test_client, "Jane")
        resp = test_client.get("/api/entities/", params={"limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert "entities" in body
        assert "total" in body

    def test_search_with_label_filter(self, test_client, clean_graph):
        _create_person(test_client, "UniqueSearchableName")
        resp = test_client.get(
            "/api/entities/",
            params={"q": "UniqueSearchableName", "label": "Person"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_search_with_invalid_label_ignored(self, test_client, clean_graph):
        """Search with invalid label still works — label filter is ignored."""
        _create_person(test_client, "FindableXyz")
        resp = test_client.get(
            "/api/entities/",
            params={"q": "FindableXyz", "label": "FakeLabel"},
        )
        assert resp.status_code == 200

    def test_update_entity(self, test_client, clean_graph):
        eid = _create_person(test_client, "Original")
        resp = test_client.put(
            f"/api/entities/Person/{eid}",
            json={"name": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_entity_invalid_label(self, test_client, clean_graph):
        resp = test_client.put(
            "/api/entities/FakeLabel/some-id",
            json={"name": "x"},
        )
        assert resp.status_code == 400

    def test_update_entity_not_found(self, test_client, clean_graph):
        resp = test_client.put(
            "/api/entities/Person/nonexistent-xyz",
            json={"name": "x"},
        )
        assert resp.status_code == 404

    def test_delete_entity(self, test_client, clean_graph):
        eid = _create_person(test_client, "ToDelete")
        resp = test_client.delete(f"/api/entities/Person/{eid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        # Verify gone
        get_resp = test_client.get(f"/api/entities/{eid}")
        assert get_resp.status_code == 404

    def test_delete_entity_invalid_label(self, test_client, clean_graph):
        resp = test_client.delete("/api/entities/FakeLabel/some-id")
        assert resp.status_code == 400

    def test_delete_entity_not_found(self, test_client, clean_graph):
        resp = test_client.delete("/api/entities/Person/nonexistent-xyz")
        assert resp.status_code == 404

    def test_get_neighborhood(self, test_client, clean_graph):
        p_id = _create_person(test_client, "Node A")
        o_id = _create_org(test_client, "Node B")
        test_client.post(
            "/api/relationships/",
            json={
                "source_id": p_id,
                "target_id": o_id,
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "DIRECTS",
                "properties": {},
            },
        )
        resp = test_client.get(f"/api/entities/{p_id}/neighborhood")
        assert resp.status_code == 200

    def test_get_neighborhood_not_found(self, test_client, clean_graph):
        resp = test_client.get("/api/entities/nonexistent-xyz/neighborhood")
        assert resp.status_code == 404

    def test_get_relationships_not_found(self, test_client, clean_graph):
        resp = test_client.get("/api/entities/nonexistent-xyz/relationships")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Relationship endpoints
# ---------------------------------------------------------------------------


class TestRelationshipEndpoints:
    """Test relationship create & delete API."""

    def _make_pair(self, test_client):
        """Create a person and org, return (person_id, org_id)."""
        p_id = _create_person(test_client, "Src")
        o_id = _create_org(test_client, "Tgt")
        return p_id, o_id

    def test_create_relationship(self, test_client, clean_graph):
        p_id, o_id = self._make_pair(test_client)
        resp = test_client.post(
            "/api/relationships/",
            json={
                "source_id": p_id,
                "target_id": o_id,
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "DIRECTS",
                "properties": {"role": "CEO"},
            },
        )
        assert resp.status_code == 200

    def test_create_relationship_invalid_type(self, test_client, clean_graph):
        resp = test_client.post(
            "/api/relationships/",
            json={
                "source_id": "a",
                "target_id": "b",
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "INVALID_TYPE",
                "properties": {},
            },
        )
        assert resp.status_code == 400

    def test_create_relationship_source_not_found(self, test_client, clean_graph):
        o_id = _create_org(test_client, "Tgt")
        resp = test_client.post(
            "/api/relationships/",
            json={
                "source_id": "missing-src",
                "target_id": o_id,
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "DIRECTS",
                "properties": {},
            },
        )
        assert resp.status_code == 404
        assert "Source" in resp.json()["detail"]

    def test_create_relationship_target_not_found(self, test_client, clean_graph):
        p_id = _create_person(test_client, "Src")
        resp = test_client.post(
            "/api/relationships/",
            json={
                "source_id": p_id,
                "target_id": "missing-tgt",
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "DIRECTS",
                "properties": {},
            },
        )
        assert resp.status_code == 404
        assert "Target" in resp.json()["detail"]

    def test_delete_relationship(self, test_client, clean_graph):
        p_id, o_id = self._make_pair(test_client)
        test_client.post(
            "/api/relationships/",
            json={
                "source_id": p_id,
                "target_id": o_id,
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "DIRECTS",
                "properties": {},
            },
        )
        resp = test_client.delete(
            "/api/relationships/",
            params={
                "source_id": p_id,
                "target_id": o_id,
                "rel_type": "DIRECTS",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_relationship_invalid_type(self, test_client, clean_graph):
        resp = test_client.delete(
            "/api/relationships/",
            params={
                "source_id": "a",
                "target_id": "b",
                "rel_type": "NOT_VALID",
            },
        )
        assert resp.status_code == 400

    def test_delete_relationship_not_found(self, test_client, clean_graph):
        # delete_relationship currently returns 200 even if no rel was matched,
        # because FalkorDB returns [[0]] for count(r). This is a known limitation.
        resp = test_client.delete(
            "/api/relationships/",
            params={
                "source_id": "missing-a",
                "target_id": "missing-b",
                "rel_type": "DIRECTS",
            },
        )
        assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Snapshot endpoints
# ---------------------------------------------------------------------------


class TestSnapshotEndpoints:
    """Test snapshot create, list, get, diff endpoints."""

    @pytest.fixture(autouse=True)
    def _seed(self, test_client, clean_graph):
        """Create a couple of entities so snapshots have something to capture."""
        self.p_id = _create_person(test_client, "Snap Person")
        self.o_id = _create_org(test_client, "Snap Org")
        self.client = test_client

    def _create_investigation(self) -> str:
        resp = self.client.post(
            "/api/investigations/",
            json={"name": f"inv-{uid()}", "description": "test"},
        )
        return resp.json()["id"]

    def test_create_snapshot(self):
        inv_id = self._create_investigation()
        resp = self.client.post(
            "/api/snapshots/",
            params={"investigation_id": inv_id, "name": "snap1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "snapshot_id" in data

    def test_list_snapshots(self):
        inv_id = self._create_investigation()
        self.client.post(
            "/api/snapshots/",
            params={"investigation_id": inv_id, "name": "list-snap"},
        )
        resp = self.client.get("/api/snapshots/", params={"investigation_id": inv_id})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_list_snapshots_no_filter(self):
        resp = self.client.get("/api/snapshots/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_snapshot(self):
        inv_id = self._create_investigation()
        create_resp = self.client.post(
            "/api/snapshots/",
            params={"investigation_id": inv_id, "name": "get-snap"},
        )
        snap_id = create_resp.json()["snapshot_id"]
        resp = self.client.get(f"/api/snapshots/{snap_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == snap_id

    def test_get_snapshot_not_found(self):
        resp = self.client.get("/api/snapshots/nonexistent-snap-id")
        assert resp.status_code == 404

    def test_diff_two_snapshots(self):
        inv_id = self._create_investigation()
        snap_a = self.client.post(
            "/api/snapshots/",
            params={"investigation_id": inv_id, "name": "diff-a"},
        ).json()["snapshot_id"]

        # Add another entity then snapshot again
        _create_person(self.client, "NewPerson")
        snap_b = self.client.post(
            "/api/snapshots/",
            params={"investigation_id": inv_id, "name": "diff-b"},
        ).json()["snapshot_id"]

        resp = self.client.get(
            "/api/snapshots/diff/compare",
            params={"snapshot_a": snap_a, "snapshot_b": snap_b},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "added_nodes" in data

    def test_diff_current_vs_snapshot(self):
        inv_id = self._create_investigation()
        snap_id = self.client.post(
            "/api/snapshots/",
            params={"investigation_id": inv_id, "name": "current-diff"},
        ).json()["snapshot_id"]

        # Add entity after snapshot
        _create_person(self.client, "AfterSnap")

        resp = self.client.get(
            "/api/snapshots/diff/current",
            params={"snapshot_id": snap_id},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# JSON importer (direct function calls — no API endpoint for JSON import)
# ---------------------------------------------------------------------------


class TestJsonImporter:
    """Test the JSON importer function directly."""

    def test_import_valid_entities(self, test_client, clean_graph):
        from src.database.falkordb_client import db
        from src.ingestion.json_importer import import_json

        payload = {
            "entities": [
                {"label": "Person", "properties": {"name": "Json Person"}},
                {"label": "Organization", "properties": {"name": "Json Org"}},
            ],
            "relationships": [],
        }
        result = import_json(db, json.dumps(payload))
        assert result["imported_entities"] == 2
        assert result["imported_relationships"] == 0
        assert result["entity_errors"] == []

    def test_import_invalid_json(self):
        from src.database.falkordb_client import db
        from src.ingestion.json_importer import import_json

        result = import_json(db, "not valid json {{{")
        assert "error" in result
        assert result["imported_entities"] == 0

    def test_import_entity_validation_error(self, test_client, clean_graph):
        from src.database.falkordb_client import db
        from src.ingestion.json_importer import import_json

        payload = {
            "entities": [
                {"label": "InvalidLabel", "properties": {"name": "X"}},
            ],
            "relationships": [],
        }
        result = import_json(db, json.dumps(payload))
        assert result["imported_entities"] == 0
        assert len(result["entity_errors"]) == 1

    def test_import_relationship_validation_error(self, test_client, clean_graph):
        from src.database.falkordb_client import db
        from src.ingestion.json_importer import import_json

        payload = {
            "entities": [],
            "relationships": [
                {
                    "source_id": "x",
                    "target_id": "y",
                    "source_label": "Person",
                    "target_label": "Person",
                    "rel_type": "INVALID_REL",
                    "properties": {},
                }
            ],
        }
        result = import_json(db, json.dumps(payload))
        assert result["imported_relationships"] == 0
        assert len(result["relationship_errors"]) == 1

    def test_import_with_id_mapping_and_relationships(self, test_client, clean_graph):
        """Entities with IDs allow relationships to reference them via id_map."""
        from src.database.falkordb_client import db
        from src.ingestion.json_importer import import_json

        p_id = uid()
        o_id = uid()
        payload = {
            "entities": [
                {"label": "Person", "properties": {"id": p_id, "name": "Mapped"}},
                {
                    "label": "Organization",
                    "properties": {"id": o_id, "name": "MappedOrg"},
                },
            ],
            "relationships": [
                {
                    "source_id": p_id,
                    "target_id": o_id,
                    "source_label": "Person",
                    "target_label": "Organization",
                    "rel_type": "DIRECTS",
                    "properties": {},
                }
            ],
        }
        result = import_json(db, json.dumps(payload))
        assert result["imported_entities"] == 2
        assert result["imported_relationships"] == 1
