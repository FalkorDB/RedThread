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

    # ---- JSON file import (happy path) ----

    def test_json_file_import_valid(self, test_client, clean_graph):
        """JSON file upload creates entities successfully."""
        import json

        payload = json.dumps(
            {
                "entities": [
                    {"label": "Person", "properties": {"name": "Json File Person"}},
                ],
                "relationships": [],
            }
        ).encode()
        files = {"file": ("data.json", io.BytesIO(payload), "application/json")}
        res = test_client.post("/api/import/json", files=files)
        assert res.status_code == 200
        assert res.json()["imported_entities"] == 1

    def test_json_file_import_invalid_json(self, test_client):
        """JSON file with unparseable content returns 400."""
        files = {"file": ("bad.json", io.BytesIO(b"not json {{"), "application/json")}
        res = test_client.post("/api/import/json", files=files)
        assert res.status_code == 400

    def test_json_file_import_non_utf8(self, test_client):
        """JSON file that isn't valid UTF-8 returns 400."""
        files = {"file": ("bad.json", io.BytesIO(b"\xff\xfe" + b"data"), "application/json")}
        res = test_client.post("/api/import/json", files=files)
        assert res.status_code == 400

    # ---- JSON inline import ----

    def test_json_inline_import_valid(self, test_client, clean_graph):
        """JSON inline import creates entities successfully."""
        payload = {
            "entities": [
                {"label": "Person", "properties": {"name": "Inline Person"}},
            ],
            "relationships": [],
        }
        res = test_client.post("/api/import/json/inline", json=payload)
        assert res.status_code == 200
        assert res.json()["imported_entities"] == 1

    def test_json_inline_import_error(self, test_client):
        """JSON inline with bad structure returns 400."""
        # Empty entities list but a relationship with invalid type
        payload = {
            "entities": [
                {"label": "FakeLabel", "properties": {"name": "x"}},
            ],
            "relationships": [],
        }
        res = test_client.post("/api/import/json/inline", json=payload)
        # Should succeed but with entity_errors
        assert res.status_code == 200
        assert res.json()["imported_entities"] == 0
        assert len(res.json()["entity_errors"]) == 1

    # ---- CSV latin-1 fallback ----

    def test_csv_entity_import_latin1_fallback(self, test_client, clean_graph):
        """CSV with latin-1 encoded characters is still importable."""
        name = "José García"
        csv_bytes = f"name,nationality\n{name},ES\n".encode("latin-1")
        files = {"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")}
        res = test_client.post("/api/import/csv/entities?label=Person", files=files)
        assert res.status_code == 200
        assert res.json()["imported"] >= 1

    def test_csv_relationship_import_latin1_fallback(self, test_client, clean_graph):
        """CSV relationships with latin-1 encoding fall back gracefully."""
        csv_bytes = (
            "source_id,target_id,source_label,target_label\nàbc,dèf,Person,Organization\n"
        ).encode("latin-1")
        files = {"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")}
        res = test_client.post("/api/import/csv/relationships?rel_type=DIRECTS", files=files)
        assert res.status_code == 200

    def test_csv_relationship_import_rejects_non_csv_file(self, test_client):
        """Relationship import rejects non-CSV files."""
        files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
        res = test_client.post("/api/import/csv/relationships?rel_type=DIRECTS", files=files)
        assert res.status_code == 400
        assert "CSV" in res.json()["detail"]
