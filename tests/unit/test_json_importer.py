"""Tests for json_importer and entity_resolver error paths."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


class TestJsonImporterExceptionPaths:
    """Cover json_importer.py lines 69-70, 105-106 — create_entity/create_relationship exceptions."""

    def test_entity_creation_exception(self):
        from src.ingestion.json_importer import import_json

        mock_client = MagicMock()
        payload = {
            "entities": [
                {"label": "Person", "properties": {"name": "Good"}},
            ],
            "relationships": [],
        }
        with patch(
            "src.ingestion.json_importer.create_entity",
            side_effect=RuntimeError("DB down"),
        ):
            result = import_json(mock_client, json.dumps(payload))
        assert result["imported_entities"] == 0
        assert len(result["entity_errors"]) == 1
        assert "DB down" in result["entity_errors"][0]["errors"][0]

    def test_relationship_creation_exception(self):
        from src.ingestion.json_importer import import_json

        mock_client = MagicMock()
        payload = {
            "entities": [],
            "relationships": [
                {
                    "rel_type": "ASSOCIATED_WITH",
                    "source_id": "s1",
                    "target_id": "t1",
                    "source_label": "Person",
                    "target_label": "Person",
                    "properties": {},
                },
            ],
        }
        with patch(
            "src.ingestion.json_importer.create_relationship",
            side_effect=RuntimeError("rel fail"),
        ):
            result = import_json(mock_client, json.dumps(payload))
        assert result["imported_relationships"] == 0
        assert len(result["relationship_errors"]) == 1
        assert "rel fail" in result["relationship_errors"][0]["errors"][0]
