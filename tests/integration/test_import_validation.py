"""Integration tests for import endpoint validation."""

from __future__ import annotations

import io


class TestImportEndpointValidation:
    """Ensure import endpoints reject invalid labels/types at the API level."""

    def test_csv_entity_import_rejects_invalid_label(self, test_client):
        csv_data = "name,nationality\nJohn Doe,US\n"
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = test_client.post("/api/import/csv/entities?label=Malicious", files=files)
        assert res.status_code == 400
        assert "Invalid entity label" in res.json()["detail"]

    def test_csv_entity_import_rejects_lowercase_label(self, test_client):
        csv_data = "name,nationality\nJohn Doe,US\n"
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = test_client.post("/api/import/csv/entities?label=person", files=files)
        assert res.status_code == 400
        assert "Invalid entity label" in res.json()["detail"]

    def test_csv_entity_import_accepts_valid_label(self, test_client):
        csv_data = "name,nationality\nImport Test Person,US\n"
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = test_client.post("/api/import/csv/entities?label=Person", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["imported"] >= 1

    def test_csv_relationship_import_rejects_invalid_type(self, test_client):
        csv_data = "source_id,target_id,source_label,target_label\ns1,t1,Person,Org\n"
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = test_client.post("/api/import/csv/relationships?rel_type=HACKS_INTO", files=files)
        assert res.status_code == 400
        assert "Invalid relationship type" in res.json()["detail"]

    def test_csv_relationship_import_rejects_lowercase_type(self, test_client):
        csv_data = "source_id,target_id,source_label,target_label\ns1,t1,Person,Org\n"
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = test_client.post("/api/import/csv/relationships?rel_type=owns", files=files)
        assert res.status_code == 400
        assert "Invalid relationship type" in res.json()["detail"]

    def test_csv_entity_import_rejects_non_csv_file(self, test_client):
        files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
        res = test_client.post("/api/import/csv/entities?label=Person", files=files)
        assert res.status_code == 400
        assert "CSV" in res.json()["detail"]

    def test_json_import_rejects_non_json_file(self, test_client):
        files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
        res = test_client.post("/api/import/json", files=files)
        assert res.status_code == 400
        assert "JSON" in res.json()["detail"]

    def test_csv_entity_import_rejects_empty_label(self, test_client):
        csv_data = "name\nTest\n"
        files = {"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = test_client.post("/api/import/csv/entities?label=", files=files)
        assert res.status_code == 400

    def test_invalid_label_in_entity_list(self, test_client):
        res = test_client.get("/api/entities/?label=FakeLabel")
        assert res.status_code == 400
        assert "Invalid label" in res.json()["detail"]
