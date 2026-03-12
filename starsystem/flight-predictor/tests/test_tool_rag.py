"""
Tests for CartON-style tool RAG.

Tests the three-stage pipeline:
1. ChromaDB query → initial hits
2. Neo4j graph traversal → relationships
3. Hierarchical aggregation → structured output
"""

import pytest
from unittest.mock import MagicMock, patch

from capability_predictor.tool_rag import (
    ToolHit,
    ServerAggregation,
    ToolDomainAggregation,
    ToolRAGResult,
    _query_chromadb,
    _traverse_tool_graph,
    _aggregate_hierarchically,
    tool_rag_carton_style,
    format_tool_rag_result,
)


# === Test Data ===

def make_tool_hit(name: str, server: str = "test-server", domain: str = "general",
                  score: float = 0.8, description: str = "") -> ToolHit:
    """Helper to create test ToolHit."""
    return ToolHit(
        name=name,
        server=server,
        domain=domain,
        description=description,
        score=score
    )


# === Unit Tests: Data Classes ===

class TestToolHit:
    def test_basic_creation(self):
        hit = make_tool_hit("get_dependency_context", "context-alignment", "code_analysis", 0.9)
        assert hit.name == "get_dependency_context"
        assert hit.server == "context-alignment"
        assert hit.domain == "code_analysis"
        assert hit.score == 0.9


class TestToolRAGResult:
    def test_to_dict_empty(self):
        result = ToolRAGResult(query="test")
        d = result.to_dict()
        assert d["query"] == "test"
        assert d["domains"] == []
        assert d["raw_hits_count"] == 0

    def test_to_dict_with_data(self):
        hit = make_tool_hit("get_dependency_context", "context-alignment", "code_analysis", 0.9)
        server = ServerAggregation(
            name="context-alignment",
            domain="code_analysis",
            tools=[hit],
            confidence=0.9
        )
        domain = ToolDomainAggregation(
            name="code_analysis",
            servers=[server],
            orphan_tools=[],
            confidence=0.9
        )
        result = ToolRAGResult(query="dependency analysis", domains=[domain], raw_hits=[hit])
        d = result.to_dict()

        assert d["query"] == "dependency analysis"
        assert len(d["domains"]) == 1
        assert d["domains"][0]["name"] == "code_analysis"
        assert d["raw_hits_count"] == 1


# === Unit Tests: Aggregation ===

class TestAggregateHierarchically:
    def test_empty_hits(self):
        graph_data = {
            "tool_to_server": {},
            "server_to_domain": {},
            "tool_to_domain": {}
        }
        result = _aggregate_hierarchically([], graph_data)
        assert result == []

    def test_tools_grouped_by_server(self):
        """Tools should be grouped by their server."""
        hits = [
            make_tool_hit("get_dependency_context", "context-alignment", "code_analysis", 0.9),
            make_tool_hit("parse_repository_to_neo4j", "context-alignment", "code_analysis", 0.85),
        ]
        graph_data = {
            "tool_to_server": {
                ("get_dependency_context", "context-alignment"): "context-alignment",
                ("parse_repository_to_neo4j", "context-alignment"): "context-alignment"
            },
            "server_to_domain": {
                "context-alignment": "code_analysis"
            },
            "tool_to_domain": {
                ("get_dependency_context", "context-alignment"): "code_analysis",
                ("parse_repository_to_neo4j", "context-alignment"): "code_analysis"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 1
        domain = result[0]
        assert domain.name == "code_analysis"
        assert len(domain.servers) == 1
        assert domain.servers[0].name == "context-alignment"
        assert len(domain.servers[0].tools) == 2
        assert len(domain.orphan_tools) == 0

    def test_orphan_tools_grouped_by_domain(self):
        """Tools without server mapping should be grouped by domain as orphans."""
        hits = [
            make_tool_hit("tool-a", "unknown", "paiab", 0.9),
            make_tool_hit("tool-b", "unknown", "paiab", 0.8),
            make_tool_hit("tool-c", "unknown", "sanctum", 0.7),
        ]
        graph_data = {
            "tool_to_server": {},  # No server mappings
            "server_to_domain": {},
            "tool_to_domain": {
                ("tool-a", "unknown"): "paiab",
                ("tool-b", "unknown"): "paiab",
                ("tool-c", "unknown"): "sanctum"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 2
        # Sorted by confidence, paiab should be first (higher avg score)
        paiab = next(d for d in result if d.name == "paiab")
        sanctum = next(d for d in result if d.name == "sanctum")

        assert len(paiab.orphan_tools) == 2
        assert len(sanctum.orphan_tools) == 1

    def test_multiple_domains_multiple_servers(self):
        """Test aggregation with multiple domains and multiple servers."""
        hits = [
            make_tool_hit("add_concept", "carton", "knowledge_graph", 0.9),
            make_tool_hit("query_wiki_graph", "carton", "knowledge_graph", 0.85),
            make_tool_hit("get_dependency_context", "context-alignment", "code_analysis", 0.8),
            make_tool_hit("orient", "starlog", "navigation", 0.75),
        ]
        graph_data = {
            "tool_to_server": {
                ("add_concept", "carton"): "carton",
                ("query_wiki_graph", "carton"): "carton",
                ("get_dependency_context", "context-alignment"): "context-alignment",
                ("orient", "starlog"): "starlog"
            },
            "server_to_domain": {
                "carton": "knowledge_graph",
                "context-alignment": "code_analysis",
                "starlog": "navigation"
            },
            "tool_to_domain": {
                ("add_concept", "carton"): "knowledge_graph",
                ("query_wiki_graph", "carton"): "knowledge_graph",
                ("get_dependency_context", "context-alignment"): "code_analysis",
                ("orient", "starlog"): "navigation"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 3
        # Sorted by confidence - knowledge_graph first (highest avg: 0.875)
        assert result[0].name == "knowledge_graph"
        assert result[0].confidence == pytest.approx(0.875, rel=0.01)

    def test_mixed_server_and_orphan(self):
        """Mix of tools in servers and orphans."""
        hits = [
            make_tool_hit("add_concept", "carton", "knowledge_graph", 0.9),
            make_tool_hit("query_wiki_graph", "carton", "knowledge_graph", 0.85),
            make_tool_hit("lone_tool", "unknown", "knowledge_graph", 0.7),
        ]
        graph_data = {
            "tool_to_server": {
                ("add_concept", "carton"): "carton",
                ("query_wiki_graph", "carton"): "carton"
                # lone_tool not mapped
            },
            "server_to_domain": {
                "carton": "knowledge_graph"
            },
            "tool_to_domain": {
                ("add_concept", "carton"): "knowledge_graph",
                ("query_wiki_graph", "carton"): "knowledge_graph",
                ("lone_tool", "unknown"): "knowledge_graph"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 1
        kg = result[0]
        assert kg.name == "knowledge_graph"
        assert len(kg.servers) == 1
        assert len(kg.servers[0].tools) == 2
        assert len(kg.orphan_tools) == 1
        assert kg.orphan_tools[0].name == "lone_tool"


# === Integration Tests (with mocks) ===

class TestToolRagCartonStyle:
    @patch('capability_predictor.tool_rag._traverse_tool_graph')
    @patch('capability_predictor.tool_rag._query_chromadb')
    def test_full_pipeline(self, mock_chroma, mock_graph):
        """Test the full RAG → Graph → Aggregation pipeline."""
        # Mock ChromaDB response
        mock_chroma.return_value = [
            make_tool_hit("get_dependency_context", "context-alignment", "code_analysis", 0.9),
            make_tool_hit("parse_repository_to_neo4j", "context-alignment", "code_analysis", 0.85),
        ]

        # Mock Neo4j response
        mock_graph.return_value = {
            "tool_to_server": {
                ("get_dependency_context", "context-alignment"): "context-alignment",
                ("parse_repository_to_neo4j", "context-alignment"): "context-alignment"
            },
            "server_to_domain": {
                "context-alignment": "code_analysis"
            },
            "tool_to_domain": {
                ("get_dependency_context", "context-alignment"): "code_analysis",
                ("parse_repository_to_neo4j", "context-alignment"): "code_analysis"
            }
        }

        result = tool_rag_carton_style("analyze code dependencies")

        assert result.query == "analyze code dependencies"
        assert len(result.domains) == 1
        assert result.domains[0].name == "code_analysis"
        assert len(result.raw_hits) == 2

    @patch('capability_predictor.tool_rag._traverse_tool_graph')
    @patch('capability_predictor.tool_rag._query_chromadb')
    def test_empty_chromadb_result(self, mock_chroma, mock_graph):
        """Test handling of no ChromaDB results."""
        mock_chroma.return_value = []

        result = tool_rag_carton_style("nonexistent query")

        assert result.query == "nonexistent query"
        assert len(result.domains) == 0
        assert len(result.raw_hits) == 0
        mock_graph.assert_not_called()  # Graph should not be queried


# === Formatting Tests ===

class TestFormatToolRagResult:
    def test_empty_result(self):
        result = ToolRAGResult(query="test")
        output = format_tool_rag_result(result)

        assert "Tool RAG Results" in output
        assert "No tool predictions found" in output

    def test_formatted_output_structure(self):
        hit = make_tool_hit("get_dependency_context", "context-alignment", "code_analysis", 0.9)
        server = ServerAggregation(
            name="context-alignment",
            domain="code_analysis",
            tools=[hit],
            confidence=0.9
        )
        domain = ToolDomainAggregation(
            name="code_analysis",
            servers=[server],
            orphan_tools=[],
            confidence=0.9
        )
        result = ToolRAGResult(query="dependency analysis", domains=[domain], raw_hits=[hit])

        output = format_tool_rag_result(result)

        assert "dependency analysis" in output
        assert "code_analysis" in output
        assert "context-alignment" in output
        assert "get_dependency_context" in output


# === Live Tests (require actual services) ===

@pytest.mark.skip(reason="Requires live ChromaDB and Neo4j")
class TestLiveToolRag:
    def test_live_query(self):
        """Test against actual ChromaDB and Neo4j."""
        result = tool_rag_carton_style("analyze code dependencies")

        assert result.query == "analyze code dependencies"
        # Should find code analysis related tools if they exist
        print(format_tool_rag_result(result))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
