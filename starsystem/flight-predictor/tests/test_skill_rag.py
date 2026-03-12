"""
Tests for CartON-style skill RAG.

Tests the three-stage pipeline:
1. ChromaDB query → initial hits
2. Neo4j graph traversal → relationships
3. Hierarchical aggregation → structured output
"""

import pytest
from unittest.mock import MagicMock, patch

from capability_predictor.skill_rag import (
    SkillHit,
    SkillsetAggregation,
    DomainAggregation,
    SkillRAGResult,
    _query_chromadb,
    _traverse_skill_graph,
    _aggregate_hierarchically,
    skill_rag_carton_style,
    format_skill_rag_result,
)


# === Test Data ===

def make_skill_hit(name: str, domain: str = "general", score: float = 0.8,
                   subdomain: str = "", category: str = "") -> SkillHit:
    """Helper to create test SkillHit."""
    return SkillHit(
        name=name,
        domain=domain,
        subdomain=subdomain,
        category=category,
        score=score
    )


# === Unit Tests: Data Classes ===

class TestSkillHit:
    def test_basic_creation(self):
        hit = make_skill_hit("test-skill", "paiab", 0.9)
        assert hit.name == "test-skill"
        assert hit.domain == "paiab"
        assert hit.score == 0.9
        assert hit.skillset is None


class TestSkillRAGResult:
    def test_to_dict_empty(self):
        result = SkillRAGResult(query="test")
        d = result.to_dict()
        assert d["query"] == "test"
        assert d["domains"] == []
        assert d["raw_hits_count"] == 0

    def test_to_dict_with_data(self):
        hit = make_skill_hit("starlog", "navigation", 0.9)
        domain = DomainAggregation(
            name="navigation",
            skillsets=[],
            orphan_skills=[hit],
            confidence=0.9
        )
        result = SkillRAGResult(query="planning", domains=[domain], raw_hits=[hit])
        d = result.to_dict()

        assert d["query"] == "planning"
        assert len(d["domains"]) == 1
        assert d["domains"][0]["name"] == "navigation"
        assert d["raw_hits_count"] == 1


# === Unit Tests: Aggregation ===

class TestAggregateHierarchically:
    def test_empty_hits(self):
        graph_data = {
            "skill_to_skillsets": {},
            "skillset_to_domain": {},
            "skill_to_domain": {}
        }
        result = _aggregate_hierarchically([], graph_data)
        assert result == []

    def test_orphan_skills_grouped_by_domain(self):
        """Skills not in skillsets should be grouped by domain as orphans."""
        hits = [
            make_skill_hit("skill-a", "paiab", 0.9),
            make_skill_hit("skill-b", "paiab", 0.8),
            make_skill_hit("skill-c", "sanctum", 0.7),
        ]
        graph_data = {
            "skill_to_skillsets": {},
            "skillset_to_domain": {},
            "skill_to_domain": {
                "skill-a": "paiab",
                "skill-b": "paiab",
                "skill-c": "sanctum"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 2
        # Sorted by confidence, paiab should be first (higher avg score)
        paiab = next(d for d in result if d.name == "paiab")
        sanctum = next(d for d in result if d.name == "sanctum")

        assert len(paiab.orphan_skills) == 2
        assert len(sanctum.orphan_skills) == 1

    def test_skills_in_skillsets_grouped(self):
        """Skills in skillsets should appear under their skillset, not as orphans."""
        hits = [
            make_skill_hit("starlog", "navigation", 0.9),
            make_skill_hit("waypoint", "navigation", 0.85),
        ]
        graph_data = {
            "skill_to_skillsets": {
                "starlog": ["navigation-skillset"],
                "waypoint": ["navigation-skillset"]
            },
            "skillset_to_domain": {
                "navigation-skillset": "navigation"
            },
            "skill_to_domain": {
                "starlog": "navigation",
                "waypoint": "navigation"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 1
        nav_domain = result[0]
        assert nav_domain.name == "navigation"
        assert len(nav_domain.skillsets) == 1
        assert nav_domain.skillsets[0].name == "navigation-skillset"
        assert len(nav_domain.skillsets[0].skills) == 2
        assert len(nav_domain.orphan_skills) == 0

    def test_mixed_skillset_and_orphan(self):
        """Mix of skills in skillsets and orphans."""
        hits = [
            make_skill_hit("starlog", "navigation", 0.9),
            make_skill_hit("waypoint", "navigation", 0.85),
            make_skill_hit("lone-skill", "navigation", 0.7),
        ]
        graph_data = {
            "skill_to_skillsets": {
                "starlog": ["nav-set"],
                "waypoint": ["nav-set"]
                # lone-skill not in any skillset
            },
            "skillset_to_domain": {
                "nav-set": "navigation"
            },
            "skill_to_domain": {
                "starlog": "navigation",
                "waypoint": "navigation",
                "lone-skill": "navigation"
            }
        }

        result = _aggregate_hierarchically(hits, graph_data)

        assert len(result) == 1
        nav = result[0]
        assert len(nav.skillsets) == 1
        assert len(nav.skillsets[0].skills) == 2
        assert len(nav.orphan_skills) == 1
        assert nav.orphan_skills[0].name == "lone-skill"


# === Integration Tests (with mocks) ===

class TestSkillRagCartonStyle:
    @patch('capability_predictor.skill_rag._traverse_skill_graph')
    @patch('capability_predictor.skill_rag._query_chromadb')
    def test_full_pipeline(self, mock_chroma, mock_graph):
        """Test the full RAG → Graph → Aggregation pipeline."""
        # Mock ChromaDB response
        mock_chroma.return_value = [
            make_skill_hit("starlog", "navigation", 0.9),
            make_skill_hit("waypoint", "navigation", 0.85),
        ]

        # Mock Neo4j response
        mock_graph.return_value = {
            "skill_to_skillsets": {
                "starlog": ["nav-set"],
                "waypoint": ["nav-set"]
            },
            "skillset_to_domain": {
                "nav-set": "navigation"
            },
            "skill_to_domain": {
                "starlog": "navigation",
                "waypoint": "navigation"
            }
        }

        result = skill_rag_carton_style("planning a project")

        assert result.query == "planning a project"
        assert len(result.domains) == 1
        assert result.domains[0].name == "navigation"
        assert len(result.raw_hits) == 2

    @patch('capability_predictor.skill_rag._traverse_skill_graph')
    @patch('capability_predictor.skill_rag._query_chromadb')
    def test_empty_chromadb_result(self, mock_chroma, mock_graph):
        """Test handling of no ChromaDB results."""
        mock_chroma.return_value = []

        result = skill_rag_carton_style("nonexistent query")

        assert result.query == "nonexistent query"
        assert len(result.domains) == 0
        assert len(result.raw_hits) == 0
        mock_graph.assert_not_called()  # Graph should not be queried


# === Formatting Tests ===

class TestFormatSkillRagResult:
    def test_empty_result(self):
        result = SkillRAGResult(query="test")
        output = format_skill_rag_result(result)

        assert "Skill RAG Results" in output
        assert "No skill predictions found" in output

    def test_formatted_output_structure(self):
        hit = make_skill_hit("starlog", "navigation", 0.9, category="preflight")
        skillset = SkillsetAggregation(
            name="nav-set",
            domain="navigation",
            skills=[hit],
            confidence=0.9
        )
        domain = DomainAggregation(
            name="navigation",
            skillsets=[skillset],
            orphan_skills=[],
            confidence=0.9
        )
        result = SkillRAGResult(query="planning", domains=[domain], raw_hits=[hit])

        output = format_skill_rag_result(result)

        assert "planning" in output
        assert "navigation" in output
        assert "nav-set" in output
        assert "starlog" in output


# === Live Tests (require actual services) ===

@pytest.mark.skip(reason="Requires live ChromaDB and Neo4j")
class TestLiveSkillRag:
    def test_live_query(self):
        """Test against actual ChromaDB and Neo4j."""
        result = skill_rag_carton_style("navigation and planning")

        assert result.query == "navigation and planning"
        # Should find navigation-related skills if they exist
        print(format_skill_rag_result(result))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
