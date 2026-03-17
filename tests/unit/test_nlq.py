"""Comprehensive tests for NLQ (Natural Language Query) module.

Covers the LLM translation path (mocked), query execution, result
formatting with different FalkorDB types, and edge cases.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.graph.nlq import (
    _enforce_limit,
    _format_result,
    _is_write_query,
    execute_nl_query,
    translate_to_cypher,
)

# ── Write query detection ───────────────────────────────────────────


class TestIsWriteQuery:
    """Additional edge cases for _is_write_query."""

    def test_set_after_return_is_safe(self):
        """SET appearing after RETURN should be allowed (e.g. alias 'data_set')."""
        query = "MATCH (n) RETURN n.data_set AS data_set LIMIT 10"
        assert _is_write_query(query) is False

    def test_set_before_return_is_unsafe(self):
        query = "MATCH (n) SET n.name = 'hack' RETURN n"
        assert _is_write_query(query) is True

    def test_set_with_no_return_is_unsafe(self):
        query = "MATCH (n) SET n.name = 'hack'"
        assert _is_write_query(query) is True

    def test_drop_is_unsafe(self):
        assert _is_write_query("DROP INDEX ON :Person(name)") is True

    def test_call_is_unsafe(self):
        assert _is_write_query("CALL db.index.fulltext.createNodeIndex('idx')") is True

    def test_detach_delete_is_unsafe(self):
        assert _is_write_query("MATCH (n) DETACH DELETE n") is True

    def test_remove_is_unsafe(self):
        assert _is_write_query("MATCH (n) REMOVE n.name") is True

    def test_case_insensitive(self):
        assert _is_write_query("match (n) create (m)") is True
        assert _is_write_query("MATCH (n) RETURN n") is False


# ── Enforce limit ───────────────────────────────────────────────────


class TestEnforceLimit:
    """Test _enforce_limit edge cases."""

    def test_caps_high_limit(self):
        q = "MATCH (n) RETURN n LIMIT 5000"
        assert "LIMIT 100" in _enforce_limit(q, max_limit=100)

    def test_keeps_low_limit(self):
        q = "MATCH (n) RETURN n LIMIT 10"
        result = _enforce_limit(q, max_limit=100)
        assert "LIMIT 10" in result

    def test_adds_limit_when_missing(self):
        q = "MATCH (n) RETURN n"
        result = _enforce_limit(q, max_limit=50)
        assert "LIMIT 50" in result

    def test_strips_trailing_semicolon(self):
        q = "MATCH (n) RETURN n;"
        result = _enforce_limit(q, max_limit=50)
        assert "LIMIT 50" in result
        assert not result.endswith(";")


# ── Format result ───────────────────────────────────────────────────


class TestFormatResult:
    """Test _format_result with different FalkorDB result types."""

    def test_scalar_values(self):
        result = MagicMock()
        result.header = ["name", "count"]
        result.result_set = [["John", 5], ["Jane", 3]]
        rows = _format_result(result)
        assert len(rows) == 2
        assert rows[0]["name"] == "John"
        assert rows[0]["count"] == 5

    def test_node_with_labels(self):
        """Nodes with .properties and .labels should be expanded."""
        node = SimpleNamespace(properties={"id": "p1", "name": "John"}, labels=["Person"])
        result = MagicMock()
        result.header = ["n"]
        result.result_set = [[node]]
        rows = _format_result(result)
        assert rows[0]["n"]["id"] == "p1"
        assert rows[0]["n"]["_label"] == "Person"

    def test_node_without_labels(self):
        node = SimpleNamespace(properties={"id": "p1"}, labels=[])
        result = MagicMock()
        result.header = ["n"]
        result.result_set = [[node]]
        rows = _format_result(result)
        assert rows[0]["n"]["id"] == "p1"
        assert "_label" not in rows[0]["n"]

    def test_path_object(self):
        """Path objects with .nodes() and .edges() should be formatted."""
        n1 = SimpleNamespace(properties={"id": "a"})
        n2 = SimpleNamespace(properties={"id": "b"})
        path = MagicMock()
        path.nodes.return_value = [n1, n2]
        path.edges.return_value = [MagicMock()]
        # Path has .nodes attribute but no .properties
        del path.properties
        result = MagicMock()
        result.header = ["path"]
        result.result_set = [[path]]
        rows = _format_result(result)
        assert rows[0]["path"]["length"] == 1
        assert len(rows[0]["path"]["nodes"]) == 2

    def test_edge_object(self):
        """Edge with .properties but no .labels gets treated as a node dict."""
        edge = SimpleNamespace(
            relation="TRANSFERRED_TO",
            src_node=1,
            dest_node=2,
            properties={"amount": 50000},
        )
        result = MagicMock()
        result.header = ["r"]
        result.result_set = [[edge]]
        rows = _format_result(result)
        # _format_result checks .properties first, so edge properties are expanded
        assert rows[0]["r"]["amount"] == 50000

    def test_no_header_uses_col_index(self):
        result = MagicMock()
        result.header = []
        result.result_set = [["value1", "value2"]]
        rows = _format_result(result)
        assert rows[0]["col_0"] == "value1"
        assert rows[0]["col_1"] == "value2"

    def test_no_header_attribute(self):
        result = SimpleNamespace(result_set=[["a", "b"]])
        rows = _format_result(result)
        assert rows[0]["col_0"] == "a"

    def test_empty_result_set(self):
        result = MagicMock()
        result.header = ["n"]
        result.result_set = []
        rows = _format_result(result)
        assert rows == []


# ── translate_to_cypher ─────────────────────────────────────────────


class TestTranslateToCypher:
    """Test translate_to_cypher with mocked LLM."""

    def test_no_api_key_returns_error(self):
        with patch("src.graph.nlq.settings") as mock_settings:
            mock_settings.llm_api_key = ""
            result = translate_to_cypher("Show me persons")
            assert result["error"]
            assert result["query"] is None

    @patch("src.graph.nlq.settings")
    def test_successful_translation(self, mock_settings: MagicMock):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = None
        mock_settings.llm_model = "gpt-4"

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="MATCH (n:Person) RETURN n LIMIT 10"))
        ]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = translate_to_cypher("Show me all persons")
            assert result["query"] == "MATCH (n:Person) RETURN n LIMIT 10"
            assert result["safe"] is True
            assert result["model"] == "gpt-4"

    @patch("src.graph.nlq.settings")
    def test_rejects_write_query_from_llm(self, mock_settings: MagicMock):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = None
        mock_settings.llm_model = "gpt-4"

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="CREATE (n:Person {name: 'hacked'})"))
        ]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = translate_to_cypher("hack the database")
            assert result["safe"] is False
            assert "write operations" in result["error"]

    @patch("src.graph.nlq.settings")
    def test_strips_markdown_fences(self, mock_settings: MagicMock):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = None
        mock_settings.llm_model = "gpt-4"

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="```cypher\nMATCH (n:Person) RETURN n LIMIT 10\n```")
            )
        ]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = translate_to_cypher("Show persons")
            assert "```" not in result["query"]
            assert result["query"].startswith("MATCH")

    @patch("src.graph.nlq.settings")
    def test_caps_high_limit_from_llm(self, mock_settings: MagicMock):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = None
        mock_settings.llm_model = "gpt-4"

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="MATCH (n:Person) RETURN n LIMIT 9999"))
        ]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = translate_to_cypher("Show all persons")
            assert "LIMIT 100" in result["query"]

    @patch("src.graph.nlq.settings")
    def test_llm_exception_handled(self, mock_settings: MagicMock):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = None
        mock_settings.llm_model = "gpt-4"

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RuntimeError("API down")
            mock_openai.return_value = mock_client

            result = translate_to_cypher("anything")
            assert "LLM translation failed" in result["error"]
            assert result["query"] is None


# ── execute_nl_query ────────────────────────────────────────────────


class TestExecuteNlQuery:
    """Test execute_nl_query with mocked translation and execution."""

    def test_returns_error_when_translation_fails(self):
        client = MagicMock()
        with patch("src.graph.nlq.settings") as mock_settings:
            mock_settings.llm_api_key = ""
            result = execute_nl_query(client, "Show persons")
            assert result["error"]
            assert result["query"] is None

    @patch("src.graph.nlq.translate_to_cypher")
    def test_executes_safe_query(self, mock_translate: MagicMock):
        mock_translate.return_value = {
            "query": "MATCH (n:Person) RETURN n.name LIMIT 10",
            "question": "Show persons",
            "model": "gpt-4",
            "safe": True,
        }

        mock_result = MagicMock()
        mock_result.header = ["n.name"]
        mock_result.result_set = [["John"], ["Jane"]]

        client = MagicMock()
        client.ro_query.return_value = mock_result

        result = execute_nl_query(client, "Show persons")
        assert result["count"] == 2
        assert result["safe"] is True

    @patch("src.graph.nlq.translate_to_cypher")
    def test_rejects_write_query(self, mock_translate: MagicMock):
        mock_translate.return_value = {
            "query": "CREATE (n:Person {name: 'bad'})",
            "question": "hack",
            "model": "gpt-4",
            "safe": True,
        }

        client = MagicMock()
        result = execute_nl_query(client, "hack")
        assert result["safe"] is False
        assert "write operations" in result["error"]
        client.ro_query.assert_not_called()

    @patch("src.graph.nlq.translate_to_cypher")
    def test_handles_execution_failure(self, mock_translate: MagicMock):
        mock_translate.return_value = {
            "query": "MATCH (n:Foo) RETURN n",
            "question": "test",
            "model": "gpt-4",
            "safe": True,
        }

        client = MagicMock()
        client.ro_query.side_effect = RuntimeError("Graph error")

        result = execute_nl_query(client, "test")
        assert "Query execution failed" in result["error"]
        assert result["safe"] is True
