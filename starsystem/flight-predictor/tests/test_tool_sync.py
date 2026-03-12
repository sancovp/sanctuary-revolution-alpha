"""Tests for tool sync to Neo4j."""

import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

from sync.sync_tools_to_neo4j import (
    infer_domain,
    create_tool_schema,
    sync_tool_to_neo4j,
    load_tools_from_catalog,
    get_catalog_stats,
    sync_all_tools,
    DOMAIN_PATTERNS
)


class TestInferDomain:
    """Tests for domain inference logic."""

    def test_server_based_inference_carton(self):
        """Should infer knowledge_graph for carton server."""
        domain = infer_domain("carton", "add_concept", "Add a concept to the graph")
        assert domain == "knowledge_graph"

    def test_server_based_inference_starship(self):
        """Should infer navigation for starship server."""
        domain = infer_domain("starship", "fly", "Start a flight")
        assert domain == "navigation"

    def test_server_based_inference_starlog(self):
        """Should infer navigation for starlog server."""
        domain = infer_domain("starlog", "orient", "Orient to project")
        assert domain == "navigation"

    def test_keyword_based_inference(self):
        """Should infer domain from description keywords."""
        domain = infer_domain(
            "unknown_server",
            "parse_code",
            "Parse and analyze the dependency graph of a repository"
        )
        assert domain == "code_analysis"

    def test_general_fallback(self):
        """Should return general for unknown patterns."""
        domain = infer_domain("xyz", "foo", "does something")
        assert domain == "general"

    def test_mcp_domain(self):
        """Should infer mcp_development for mcpify server."""
        domain = infer_domain("mcpify", "create_server", "Create MCP server")
        assert domain == "mcp_development"


class TestCreateToolSchema:
    """Tests for schema creation."""

    def test_creates_constraints_and_indexes(self):
        """Should execute all schema queries."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

        result = create_tool_schema(mock_driver)

        assert result["schema_created"] is True
        assert len(result["results"]) == 6  # 3 constraints + 3 indexes
        assert all(r["status"] == "success" for r in result["results"])

    def test_handles_constraint_errors(self):
        """Should handle errors gracefully."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Constraint already exists")
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

        result = create_tool_schema(mock_driver)

        assert result["schema_created"] is True
        assert all(r["status"] == "error" for r in result["results"])


class TestSyncToolToNeo4j:
    """Tests for individual tool sync."""

    def test_syncs_tool_with_all_relationships(self):
        """Should create tool, server, and domain nodes with relationships."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {
            "tool_name": "add_concept",
            "server_name": "carton",
            "domain_name": "knowledge_graph"
        }
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

        tool_data = {
            "name": "add_concept",
            "description": "Add a concept",
            "server": "carton",
            "domain": "knowledge_graph"
        }

        result = sync_tool_to_neo4j(mock_driver, tool_data)

        assert result["tool"] == "add_concept"
        assert result["server"] == "carton"
        assert result["domain"] == "knowledge_graph"
        assert result["status"] == "synced"


class TestLoadToolsFromCatalog:
    """Tests for loading tools from catalog file."""

    def test_loads_tools_from_catalog(self):
        """Should load tools and infer domains."""
        catalog_data = {
            "carton": [
                {"name": "add_concept", "description": "Add a concept to the graph"},
                {"name": "query_wiki_graph", "description": "Query the wiki graph"}
            ],
            "starship": [
                {"name": "fly", "description": "Start a flight config"}
            ]
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(catalog_data))):
            with patch("os.path.exists", return_value=True):
                tools = load_tools_from_catalog("/fake/path.json")

        assert len(tools) == 3
        assert tools[0]["name"] == "add_concept"
        assert tools[0]["server"] == "carton"
        assert tools[0]["domain"] == "knowledge_graph"
        assert tools[2]["server"] == "starship"
        assert tools[2]["domain"] == "navigation"

    def test_returns_empty_for_missing_file(self):
        """Should return empty list if catalog not found."""
        with patch("os.path.exists", return_value=False):
            tools = load_tools_from_catalog("/nonexistent/path.json")

        assert tools == []

    def test_truncates_long_descriptions(self):
        """Should truncate descriptions longer than 2000 chars."""
        catalog_data = {
            "test": [{"name": "tool", "description": "x" * 5000}]
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(catalog_data))):
            with patch("os.path.exists", return_value=True):
                tools = load_tools_from_catalog("/fake/path.json")

        assert len(tools[0]["description"]) == 2000


class TestGetCatalogStats:
    """Tests for catalog statistics."""

    def test_returns_stats(self):
        """Should return catalog statistics."""
        catalog_data = {
            "server1": [{"name": "t1"}, {"name": "t2"}],
            "server2": [{"name": "t3"}]
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(catalog_data))):
            with patch("os.path.exists", return_value=True):
                stats = get_catalog_stats("/fake/path.json")

        assert stats["server_count"] == 2
        assert stats["total_tools"] == 3
        assert stats["tools_per_server"]["server1"] == 2
        assert stats["tools_per_server"]["server2"] == 1

    def test_handles_missing_file(self):
        """Should return error for missing file."""
        with patch("os.path.exists", return_value=False):
            stats = get_catalog_stats("/nonexistent/path.json")

        assert "error" in stats


class TestSyncAllTools:
    """Tests for full sync operation."""

    @patch("sync.sync_tools_to_neo4j.get_neo4j_driver")
    @patch("sync.sync_tools_to_neo4j.load_tools_from_catalog")
    @patch("sync.sync_tools_to_neo4j.create_tool_schema")
    @patch("sync.sync_tools_to_neo4j.sync_tool_to_neo4j")
    def test_syncs_all_tools(self, mock_sync_tool, mock_create_schema,
                             mock_load_tools, mock_get_driver):
        """Should sync all tools and return summary."""
        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        mock_create_schema.return_value = {"schema_created": True, "results": []}

        mock_load_tools.return_value = [
            {"name": "t1", "description": "Tool 1", "server": "s1", "domain": "d1"},
            {"name": "t2", "description": "Tool 2", "server": "s1", "domain": "d1"},
            {"name": "t3", "description": "Tool 3", "server": "s2", "domain": "d2"},
        ]

        mock_sync_tool.return_value = {"status": "synced", "tool": "test"}

        result = sync_all_tools()

        assert result["tools_synced"] == 3
        assert result["tools_total"] == 3
        assert result["servers_count"] == 2
        assert result["domains_count"] == 2
        mock_driver.close.assert_called_once()

    @patch("sync.sync_tools_to_neo4j.get_neo4j_driver")
    @patch("sync.sync_tools_to_neo4j.load_tools_from_catalog")
    @patch("sync.sync_tools_to_neo4j.create_tool_schema")
    @patch("sync.sync_tools_to_neo4j.sync_tool_to_neo4j")
    def test_handles_sync_errors(self, mock_sync_tool, mock_create_schema,
                                 mock_load_tools, mock_get_driver):
        """Should handle individual tool sync errors."""
        mock_driver = MagicMock()
        mock_get_driver.return_value = mock_driver

        mock_create_schema.return_value = {"schema_created": True, "results": []}

        mock_load_tools.return_value = [
            {"name": "t1", "description": "Tool 1", "server": "s1", "domain": "d1"},
        ]

        mock_sync_tool.side_effect = Exception("Sync failed")

        result = sync_all_tools()

        assert result["tools_synced"] == 0
        assert result["tools_total"] == 1
        assert result["tool_results"][0]["status"] == "error"


class TestDomainPatterns:
    """Tests for domain pattern completeness."""

    def test_all_patterns_have_required_keys(self):
        """All domain patterns should have servers and keywords."""
        for domain, patterns in DOMAIN_PATTERNS.items():
            assert "servers" in patterns, f"{domain} missing 'servers'"
            assert "keywords" in patterns, f"{domain} missing 'keywords'"
            assert isinstance(patterns["servers"], list)
            assert isinstance(patterns["keywords"], list)

    def test_no_duplicate_servers(self):
        """No server should appear in multiple domains."""
        all_servers = []
        for patterns in DOMAIN_PATTERNS.values():
            all_servers.extend(patterns["servers"])

        duplicates = [s for s in all_servers if all_servers.count(s) > 1]
        # All duplicates should be intentional
        allowed_duplicates = []  # Currently no duplicates expected
        unexpected_duplicates = [d for d in duplicates if d not in allowed_duplicates]

        assert unexpected_duplicates == [], f"Unexpected duplicate servers: {set(unexpected_duplicates)}"
