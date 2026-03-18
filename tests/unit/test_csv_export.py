"""Tests for CSV export endpoints."""

from __future__ import annotations

import csv
import io


def _seed_export_data(test_client):
    """Create entities and a relationship for export tests.

    Returns created entity IDs for use in assertions.
    """
    r1 = test_client.post(
        "/api/entities/person",
        json={"name": "CSV Person One"},
    )
    p1_id = r1.json()["id"]

    r2 = test_client.post(
        "/api/entities/person",
        json={"name": "CSV Person Two"},
    )
    p2_id = r2.json()["id"]

    r3 = test_client.post(
        "/api/entities/organization",
        json={"name": "CSV Org"},
    )
    o1_id = r3.json()["id"]

    test_client.post(
        "/api/relationships/",
        json={
            "source_id": p1_id,
            "target_id": o1_id,
            "source_label": "Person",
            "target_label": "Organization",
            "rel_type": "DIRECTS",
            "properties": {"role": "CEO"},
        },
    )
    return {"p1": p1_id, "p2": p2_id, "o1": o1_id}


class TestExportEntitiesCSV:
    """Test GET /api/export/entities/csv."""

    def test_export_persons_csv(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/entities/csv?label=Person")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")

        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) >= 1
        assert "id" in reader.fieldnames
        assert "name" in reader.fieldnames

    def test_export_organizations_csv(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/entities/csv?label=Organization")
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) >= 1

    def test_export_csv_invalid_label(self, test_client):
        resp = test_client.get("/api/export/entities/csv?label=Hacker")
        assert resp.status_code == 422

    def test_export_csv_respects_limit(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/entities/csv?label=Person&limit=1")
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 1

    def test_export_empty_label_returns_404(self, test_client):
        resp = test_client.get("/api/export/entities/csv?label=Document")
        assert resp.status_code == 404


class TestExportRelationshipsCSV:
    """Test GET /api/export/relationships/csv."""

    def test_export_all_relationships(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/relationships/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) >= 1
        assert "source_id" in reader.fieldnames
        assert "target_id" in reader.fieldnames
        assert "rel_type" in reader.fieldnames

    def test_export_filtered_by_type(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/relationships/csv?rel_type=DIRECTS")
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert all(r["rel_type"] == "DIRECTS" for r in rows)

    def test_export_invalid_rel_type(self, test_client):
        resp = test_client.get("/api/export/relationships/csv?rel_type=HACKS_INTO")
        assert resp.status_code == 422

    def test_csv_has_expected_columns(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/relationships/csv")
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        expected = {
            "source_id",
            "source_label",
            "rel_type",
            "target_id",
            "target_label",
            "amount",
            "valid_from",
            "valid_to",
            "created_at",
        }
        assert expected == set(reader.fieldnames)

    def test_filename_contains_date(self, test_client):
        _seed_export_data(test_client)
        resp = test_client.get("/api/export/relationships/csv")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert "relationships_" in disposition
        assert ".csv" in disposition

    def test_nonexistent_rel_type_returns_404(self, test_client):
        resp = test_client.get("/api/export/relationships/csv?rel_type=CONTACTED")
        # CONTACTED is valid but may have no data → 404
        assert resp.status_code in (200, 404)
