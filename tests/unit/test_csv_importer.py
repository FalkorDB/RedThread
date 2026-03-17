"""Tests for CSV importer — entity and relationship import from CSV content."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.csv_importer import import_entities_csv, import_relationships_csv


@pytest.fixture()
def mock_client() -> MagicMock:
    return MagicMock()


class TestImportEntitiesCsv:
    """Test CSV entity import with various inputs."""

    def test_import_valid_persons(self, mock_client):
        csv = "id,name,nationality\np-1,Alice,US\np-2,Bob,UK\n"
        with patch("src.ingestion.csv_importer.create_entity") as mock_create:
            result = import_entities_csv(mock_client, csv, "Person")
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == []
        assert mock_create.call_count == 2

    def test_import_with_column_mapping(self, mock_client):
        csv = "full_name,country\nAlice,US\n"
        mapping = {"full_name": "name", "country": "nationality"}
        with patch("src.ingestion.csv_importer.create_entity") as mock_create:
            result = import_entities_csv(mock_client, csv, "Person", column_mapping=mapping)
        assert result["imported"] == 1
        call_data = mock_create.call_args[0][2]
        assert call_data["name"] == "Alice"
        assert call_data["nationality"] == "US"

    def test_empty_csv(self, mock_client):
        csv = "id,name\n"
        result = import_entities_csv(mock_client, csv, "Person")
        assert result["imported"] == 0
        assert result["skipped"] == 0

    def test_strips_whitespace(self, mock_client):
        csv = "id,name\np-1,  Alice  \n"
        with patch("src.ingestion.csv_importer.create_entity") as mock_create:
            import_entities_csv(mock_client, csv, "Person")
        call_data = mock_create.call_args[0][2]
        assert call_data["name"] == "Alice"

    def test_skips_empty_values(self, mock_client):
        csv = "id,name,dob\np-1,Alice,\n"
        with patch("src.ingestion.csv_importer.create_entity") as mock_create:
            import_entities_csv(mock_client, csv, "Person")
        call_data = mock_create.call_args[0][2]
        assert "dob" not in call_data

    def test_validation_error_skips_row(self, mock_client):
        csv = "id,name,risk_score\np-1,,50\n"
        with patch("src.ingestion.csv_importer.create_entity") as mock_create:
            result = import_entities_csv(mock_client, csv, "Person")
        assert result["imported"] == 0
        assert result["skipped"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["row"] == 2
        mock_create.assert_not_called()

    def test_create_entity_exception_caught(self, mock_client):
        csv = "id,name\np-1,Alice\n"
        with patch(
            "src.ingestion.csv_importer.create_entity",
            side_effect=RuntimeError("DB error"),
        ):
            result = import_entities_csv(mock_client, csv, "Person")
        assert result["imported"] == 0
        assert result["skipped"] == 1
        assert "DB error" in result["errors"][0]["errors"][0]

    def test_mixed_valid_and_invalid_rows(self, mock_client):
        csv = "id,name\np-1,Alice\np-2,\np-3,Charlie\n"
        with patch("src.ingestion.csv_importer.create_entity"):
            result = import_entities_csv(mock_client, csv, "Person")
        assert result["imported"] == 2
        assert result["skipped"] == 1

    def test_mapping_ignores_unmapped_columns(self, mock_client):
        csv = "name_col,extra_col\nAlice,ignored\n"
        mapping = {"name_col": "name"}
        with patch("src.ingestion.csv_importer.create_entity") as mock_create:
            import_entities_csv(mock_client, csv, "Person", column_mapping=mapping)
        call_data = mock_create.call_args[0][2]
        assert "extra_col" not in call_data
        assert "ignored" not in call_data.values()


class TestImportRelationshipsCsv:
    """Test CSV relationship import."""

    _header = "source_id,target_id,source_label,target_label"

    def test_import_valid_relationships(self, mock_client):
        csv = f"{self._header}\np-1,o-1,Person,Organization\np-2,o-2,Person,Organization\n"
        with patch("src.ingestion.csv_importer.create_relationship") as mock_create:
            result = import_relationships_csv(mock_client, csv, "DIRECTS")
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert mock_create.call_count == 2

    def test_extra_props_passed_through(self, mock_client):
        csv = f"{self._header},role\np-1,o-1,Person,Organization,director\n"
        with patch("src.ingestion.csv_importer.create_relationship") as mock_create:
            import_relationships_csv(mock_client, csv, "DIRECTS")
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["properties"] == {"role": "director"}

    def test_validation_error_skips_row(self, mock_client):
        csv = f"{self._header}\n,o-1,Person,Organization\n"
        with patch("src.ingestion.csv_importer.create_relationship") as mock_create:
            result = import_relationships_csv(mock_client, csv, "DIRECTS")
        assert result["skipped"] == 1
        assert result["imported"] == 0
        mock_create.assert_not_called()

    def test_create_relationship_exception_caught(self, mock_client):
        csv = f"{self._header}\np-1,o-1,Person,Organization\n"
        with patch(
            "src.ingestion.csv_importer.create_relationship",
            side_effect=RuntimeError("Graph error"),
        ):
            result = import_relationships_csv(mock_client, csv, "DIRECTS")
        assert result["imported"] == 0
        assert result["skipped"] == 1
        assert "Graph error" in result["errors"][0]["errors"][0]

    def test_column_mapping(self, mock_client):
        csv = "src,tgt,src_type,tgt_type\np-1,o-1,Person,Organization\n"
        mapping = {
            "src": "source_id",
            "tgt": "target_id",
            "src_type": "source_label",
            "tgt_type": "target_label",
        }
        with patch("src.ingestion.csv_importer.create_relationship") as mock_create:
            result = import_relationships_csv(mock_client, csv, "DIRECTS", column_mapping=mapping)
        assert result["imported"] == 1
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["source_id"] == "p-1"
        assert call_kwargs["target_id"] == "o-1"

    def test_empty_csv(self, mock_client):
        csv = f"{self._header}\n"
        result = import_relationships_csv(mock_client, csv, "DIRECTS")
        assert result["imported"] == 0
        assert result["skipped"] == 0

    def test_base_fields_excluded_from_properties(self, mock_client):
        csv = f"{self._header},amount\np-1,o-1,Account,Account,5000\n"
        with patch("src.ingestion.csv_importer.create_relationship") as mock_create:
            import_relationships_csv(mock_client, csv, "TRANSFERRED_TO")
        call_kwargs = mock_create.call_args[1]
        props = call_kwargs["properties"]
        assert "source_id" not in props
        assert "target_id" not in props
        assert props.get("amount") == "5000"
