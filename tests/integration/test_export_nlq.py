"""Tests for export endpoints and NLQ safety checks."""

from __future__ import annotations


class TestExportSubgraph:
    """Test subgraph export endpoint."""

    def test_export_existing_entity(self, test_client):
        # Create an entity to export
        res = test_client.post(
            "/api/entities/person",
            json={"name": "Export Subject", "nationality": "US"},
        )
        entity_id = res.json()["id"]

        res = test_client.get(f"/api/export/subgraph?entity_id={entity_id}")
        assert res.status_code == 200
        data = res.json()
        assert "exported_at" in data
        assert "entities" in data
        assert "relationships" in data
        assert data["center_entity"] == entity_id

    def test_export_nonexistent_entity_returns_404(self, test_client):
        res = test_client.get("/api/export/subgraph?entity_id=nonexistent-id")
        assert res.status_code == 404

    def test_export_entities_have_label_and_properties(self, test_client):
        res = test_client.post(
            "/api/entities/organization",
            json={"name": "Export Org", "jurisdiction": "Panama"},
        )
        entity_id = res.json()["id"]

        res = test_client.get(f"/api/export/subgraph?entity_id={entity_id}")
        data = res.json()
        for ent in data["entities"]:
            assert "label" in ent
            assert "properties" in ent
            # Properties should NOT contain 'label' key
            assert "label" not in ent["properties"]

    def test_export_respects_depth_param(self, test_client):
        res = test_client.post("/api/entities/person", json={"name": "Depth Test"})
        entity_id = res.json()["id"]

        res = test_client.get(f"/api/export/subgraph?entity_id={entity_id}&depth=1&limit=10")
        assert res.status_code == 200
        assert res.json()["depth"] == 1


class TestExportReport:
    """Test report generation endpoint."""

    def test_report_for_existing_entity(self, test_client):
        res = test_client.post(
            "/api/entities/person",
            json={"name": "Report Subject", "risk_score": 40},
        )
        entity_id = res.json()["id"]

        res = test_client.get(f"/api/export/report?entity_id={entity_id}")
        assert res.status_code == 200
        data = res.json()
        assert "generated_at" in data
        assert "subject" in data
        assert "risk_assessment" in data
        assert "relationships" in data
        assert "network_summary" in data

    def test_report_nonexistent_returns_404(self, test_client):
        res = test_client.get("/api/export/report?entity_id=nonexistent-id")
        assert res.status_code == 404


class TestGraphSnapshot:
    """Test full graph snapshot export."""

    def test_snapshot_returns_entities(self, test_client):
        res = test_client.get("/api/export/graph-snapshot")
        assert res.status_code == 200
        data = res.json()
        assert "exported_at" in data
        assert "entities" in data
        assert "entity_count" in data
        assert isinstance(data["entities"], list)

    def test_snapshot_respects_limit(self, test_client):
        res = test_client.get("/api/export/graph-snapshot?limit=5")
        assert res.status_code == 200

    def test_snapshot_does_not_mutate_cached_entities(self, test_client, clean_graph):
        """Regression: export must not pop 'label' from entity dicts."""
        test_client.post("/api/entities/person", json={"name": "Immutable"})

        # Call snapshot twice — if the first call mutates, second will differ
        res1 = test_client.get("/api/export/graph-snapshot")
        res2 = test_client.get("/api/export/graph-snapshot")
        assert res1.status_code == 200
        assert res2.status_code == 200

        # Both should have entities with label and properties
        for ent in res1.json()["entities"]:
            assert "label" in ent
            assert "properties" in ent

        for ent in res2.json()["entities"]:
            assert "label" in ent
            assert "properties" in ent


class TestNLQWriteQueryDetection:
    """Test the NLQ safety check — write query detection."""

    def test_rejects_create(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("CREATE (n:Person {name: 'Bad'})") is True

    def test_rejects_delete(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("MATCH (n) DELETE n") is True

    def test_rejects_detach_delete(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("MATCH (n) DETACH DELETE n") is True

    def test_rejects_set(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("MATCH (n:Person) SET n.name = 'Hacked'") is True

    def test_rejects_merge(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("MERGE (n:Person {name: 'Test'})") is True

    def test_rejects_remove(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("MATCH (n:Person) REMOVE n.name") is True

    def test_rejects_drop(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("DROP INDEX ON :Person(name)") is True

    def test_rejects_call(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("CALL db.idx.fulltext.queryNodes('Person', 'test')") is True

    def test_allows_read_only(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("MATCH (n:Person) RETURN n LIMIT 10") is False

    def test_allows_complex_read(self):
        from src.graph.nlq import _is_write_query

        query = (
            "MATCH path = (a:Person)-[:DIRECTS*1..3]->(o:Organization) "
            "WHERE a.nationality = 'Hungarian' "
            "RETURN a.name, o.name, length(path) ORDER BY length(path) LIMIT 20"
        )
        assert _is_write_query(query) is False

    def test_allows_set_in_return_alias(self):
        from src.graph.nlq import _is_write_query

        # "SET" appearing after RETURN should not be flagged
        query = "MATCH (n) RETURN n.name AS data_set LIMIT 10"
        assert _is_write_query(query) is False

    def test_case_insensitive_detection(self):
        from src.graph.nlq import _is_write_query

        assert _is_write_query("match (n) create (m)") is True
        assert _is_write_query("MATCH (n) delete n") is True


class TestNLQEnforceLimit:
    """Test the LIMIT enforcement function."""

    def test_adds_limit_when_missing(self):
        from src.graph.nlq import _enforce_limit

        result = _enforce_limit("MATCH (n) RETURN n")
        assert "LIMIT" in result

    def test_caps_excessive_limit(self):
        from src.graph.nlq import _enforce_limit

        result = _enforce_limit("MATCH (n) RETURN n LIMIT 999", max_limit=100)
        assert "LIMIT 100" in result

    def test_preserves_reasonable_limit(self):
        from src.graph.nlq import _enforce_limit

        result = _enforce_limit("MATCH (n) RETURN n LIMIT 25", max_limit=100)
        assert "LIMIT 25" in result

    def test_strips_trailing_semicolon(self):
        from src.graph.nlq import _enforce_limit

        result = _enforce_limit("MATCH (n) RETURN n;")
        assert result.endswith("LIMIT 100") or "LIMIT" in result
        assert not result.endswith(";")

    def test_custom_max_limit(self):
        from src.graph.nlq import _enforce_limit

        result = _enforce_limit("MATCH (n) RETURN n LIMIT 50", max_limit=30)
        assert "LIMIT 30" in result


class TestNLQTranslationFallback:
    """Test NLQ graceful degradation when LLM is not configured."""

    def test_returns_error_when_no_api_key(self):
        from src.graph.nlq import translate_to_cypher

        result = translate_to_cypher("Show me all persons")
        # Since we're in test env without LLM key
        assert result.get("error") or result.get("query")
        assert "question" in result

    def test_nlq_api_returns_error_or_result(self, test_client):
        res = test_client.post(
            "/api/nlq/query",
            json={"question": "Show me all persons"},
        )
        assert res.status_code == 200
        data = res.json()
        # Either has error (no LLM key) or results
        assert "error" in data or "results" in data

    def test_nlq_examples_endpoint(self, test_client):
        res = test_client.get("/api/nlq/examples")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
