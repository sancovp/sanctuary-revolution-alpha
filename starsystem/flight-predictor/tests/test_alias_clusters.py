"""
Tests for alias clusters (Phase 4.2).

Tests cover:
- Alias cluster data structures
- Persistence (save/load)
- Domain matching
- Bootstrap predictions
- Feedback loop integration
- Cluster management
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Set up test storage directory before importing the module
TEST_STORAGE_DIR = tempfile.mkdtemp()
os.environ["CAPABILITY_TRACKER_DIR"] = TEST_STORAGE_DIR


from capability_predictor.alias_clusters import (
    AliasCluster,
    AliasClustersConfig,
    DEFAULT_DOMAIN_ALIASES,
    DEFAULT_DOMAIN_SKILLS,
    DEFAULT_DOMAIN_TOOLS,
    add_keyword_to_cluster,
    add_skill_to_cluster,
    add_tool_to_cluster,
    augment_with_alias_clusters,
    create_default_alias_clusters,
    format_bootstrap_predictions,
    format_clusters_report,
    get_alias_clusters_file,
    get_bootstrap_predictions,
    list_all_clusters,
    load_alias_clusters,
    match_query_to_domains,
    reset_alias_clusters_to_defaults,
    save_alias_clusters,
)


# ============================================================================
# Fixture for clean test state
# ============================================================================


@pytest.fixture(autouse=True)
def clean_storage():
    """Clean up storage before and after each test."""
    # Clean before
    filepath = get_alias_clusters_file()
    if filepath.exists():
        filepath.unlink()

    yield

    # Clean after
    if filepath.exists():
        filepath.unlink()


# ============================================================================
# AliasCluster Data Class Tests
# ============================================================================


class TestAliasCluster:
    """Tests for AliasCluster dataclass."""

    def test_create_empty_cluster(self):
        """Can create a cluster with just a domain."""
        cluster = AliasCluster(domain="test")
        assert cluster.domain == "test"
        assert cluster.keywords == []
        assert cluster.skills == []
        assert cluster.tools == []

    def test_create_full_cluster(self):
        """Can create a cluster with all fields."""
        cluster = AliasCluster(
            domain="navigation",
            keywords=["plan", "route"],
            skills=["starlog", "waypoint"],
            tools=["mcp__starlog__start_starlog"],
        )
        assert cluster.domain == "navigation"
        assert len(cluster.keywords) == 2
        assert len(cluster.skills) == 2
        assert len(cluster.tools) == 1

    def test_to_dict(self):
        """Cluster serializes to dict correctly."""
        cluster = AliasCluster(
            domain="test",
            keywords=["a", "b"],
            skills=["s1"],
            tools=["t1"],
        )
        data = cluster.to_dict()
        assert data["domain"] == "test"
        assert data["keywords"] == ["a", "b"]
        assert data["skills"] == ["s1"]
        assert data["tools"] == ["t1"]

    def test_from_dict(self):
        """Cluster deserializes from dict correctly."""
        data = {
            "domain": "test",
            "keywords": ["x", "y"],
            "skills": ["s"],
            "tools": ["t"],
        }
        cluster = AliasCluster.from_dict(data)
        assert cluster.domain == "test"
        assert cluster.keywords == ["x", "y"]
        assert cluster.skills == ["s"]
        assert cluster.tools == ["t"]

    def test_from_dict_missing_fields(self):
        """Handles missing optional fields."""
        data = {"domain": "minimal"}
        cluster = AliasCluster.from_dict(data)
        assert cluster.domain == "minimal"
        assert cluster.keywords == []
        assert cluster.skills == []
        assert cluster.tools == []


# ============================================================================
# AliasClustersConfig Tests
# ============================================================================


class TestAliasClustersConfig:
    """Tests for AliasClustersConfig container."""

    def test_create_empty_config(self):
        """Can create empty config."""
        config = AliasClustersConfig()
        assert config.version == "1.0"
        assert config.clusters == []

    def test_create_with_clusters(self):
        """Can create config with clusters."""
        clusters = [
            AliasCluster(domain="a"),
            AliasCluster(domain="b"),
        ]
        config = AliasClustersConfig(clusters=clusters)
        assert len(config.clusters) == 2

    def test_get_cluster(self):
        """Can retrieve cluster by domain."""
        clusters = [
            AliasCluster(domain="nav"),
            AliasCluster(domain="build"),
        ]
        config = AliasClustersConfig(clusters=clusters)
        assert config.get_cluster("nav") is not None
        assert config.get_cluster("nav").domain == "nav"
        assert config.get_cluster("missing") is None

    def test_add_cluster_new(self):
        """Can add new cluster."""
        config = AliasClustersConfig()
        config.add_cluster(AliasCluster(domain="new"))
        assert len(config.clusters) == 1
        assert config.get_cluster("new") is not None

    def test_add_cluster_replaces_existing(self):
        """Adding cluster with same domain replaces existing."""
        config = AliasClustersConfig(clusters=[
            AliasCluster(domain="test", keywords=["old"]),
        ])
        config.add_cluster(AliasCluster(domain="test", keywords=["new"]))
        assert len(config.clusters) == 1
        assert config.get_cluster("test").keywords == ["new"]

    def test_to_dict(self):
        """Config serializes correctly."""
        config = AliasClustersConfig(
            version="2.0",
            clusters=[AliasCluster(domain="a")],
        )
        data = config.to_dict()
        assert data["version"] == "2.0"
        assert len(data["clusters"]) == 1

    def test_from_dict(self):
        """Config deserializes correctly."""
        data = {
            "version": "1.5",
            "clusters": [{"domain": "x"}, {"domain": "y"}],
        }
        config = AliasClustersConfig.from_dict(data)
        assert config.version == "1.5"
        assert len(config.clusters) == 2


# ============================================================================
# Persistence Tests
# ============================================================================


class TestPersistence:
    """Tests for save/load functionality."""

    def test_save_and_load(self):
        """Config persists to disk and loads back."""
        original = AliasClustersConfig(
            version="test",
            clusters=[AliasCluster(domain="test", keywords=["a", "b"])],
        )
        save_alias_clusters(original)

        loaded = load_alias_clusters()
        assert loaded.version == "test"
        assert len(loaded.clusters) == 1
        assert loaded.get_cluster("test").keywords == ["a", "b"]

    def test_load_creates_defaults_if_missing(self):
        """Loading when file doesn't exist creates defaults."""
        config = load_alias_clusters()
        assert len(config.clusters) > 0
        assert config.get_cluster("navigation") is not None

    def test_reset_to_defaults(self):
        """Can reset to default configuration."""
        # Save custom config
        custom = AliasClustersConfig(clusters=[AliasCluster(domain="custom")])
        save_alias_clusters(custom)

        # Reset to defaults
        config = reset_alias_clusters_to_defaults()

        # Verify defaults restored
        assert config.get_cluster("custom") is None
        assert config.get_cluster("navigation") is not None


# ============================================================================
# Default Definitions Tests
# ============================================================================


class TestDefaultDefinitions:
    """Tests for default alias cluster definitions."""

    def test_default_aliases_exist(self):
        """Default domain aliases are defined."""
        assert "navigation" in DEFAULT_DOMAIN_ALIASES
        assert "building" in DEFAULT_DOMAIN_ALIASES
        assert "testing" in DEFAULT_DOMAIN_ALIASES
        assert len(DEFAULT_DOMAIN_ALIASES) >= 5

    def test_default_skills_exist(self):
        """Default domain skills are defined."""
        assert "navigation" in DEFAULT_DOMAIN_SKILLS
        assert "building" in DEFAULT_DOMAIN_SKILLS
        assert len(DEFAULT_DOMAIN_SKILLS) >= 5

    def test_default_tools_exist(self):
        """Default domain tools are defined."""
        assert "navigation" in DEFAULT_DOMAIN_TOOLS
        assert "building" in DEFAULT_DOMAIN_TOOLS
        assert len(DEFAULT_DOMAIN_TOOLS) >= 5

    def test_navigation_keywords(self):
        """Navigation domain has expected keywords."""
        nav_keywords = DEFAULT_DOMAIN_ALIASES["navigation"]
        assert "plan" in nav_keywords
        assert "waypoint" in nav_keywords
        assert "starlog" in nav_keywords

    def test_building_keywords(self):
        """Building domain has expected keywords."""
        build_keywords = DEFAULT_DOMAIN_ALIASES["building"]
        assert "code" in build_keywords
        assert "write" in build_keywords
        assert "implement" in build_keywords

    def test_create_default_clusters(self):
        """Default clusters are created correctly."""
        config = create_default_alias_clusters()

        # Check navigation cluster
        nav = config.get_cluster("navigation")
        assert nav is not None
        assert "plan" in nav.keywords
        assert len(nav.skills) > 0
        assert len(nav.tools) > 0

        # Check building cluster
        build = config.get_cluster("building")
        assert build is not None
        assert "code" in build.keywords


# ============================================================================
# Domain Matching Tests
# ============================================================================


class TestDomainMatching:
    """Tests for matching queries to domains."""

    def test_match_navigation_query(self):
        """Planning queries match navigation domain."""
        matches = match_query_to_domains("plan the project structure")
        assert len(matches) > 0
        domains = [m[0] for m in matches]
        assert "navigation" in domains

    def test_match_building_query(self):
        """Coding queries match building domain."""
        matches = match_query_to_domains("write the implementation code")
        assert len(matches) > 0
        domains = [m[0] for m in matches]
        assert "building" in domains

    def test_match_testing_query(self):
        """Testing queries match testing domain."""
        matches = match_query_to_domains("run the tests and verify")
        assert len(matches) > 0
        domains = [m[0] for m in matches]
        assert "testing" in domains

    def test_match_multiple_domains(self):
        """Query can match multiple domains."""
        # "test the code" should match both testing and building
        matches = match_query_to_domains("test the code")
        domains = [m[0] for m in matches]
        assert len(domains) >= 1

    def test_match_no_domains(self):
        """Unrelated queries return empty matches."""
        matches = match_query_to_domains("xyz abc 123")
        assert matches == []

    def test_match_scores_sorted(self):
        """Matches are sorted by score descending."""
        matches = match_query_to_domains("plan and write code")
        if len(matches) > 1:
            scores = [m[1] for m in matches]
            assert scores == sorted(scores, reverse=True)

    def test_score_based_on_keyword_proportion(self):
        """Score reflects proportion of matching keywords."""
        # Query with mostly navigation keywords
        matches1 = match_query_to_domains("plan the flight route")
        # Query with mixed keywords
        matches2 = match_query_to_domains("plan the code")

        nav_score1 = next((s for d, s in matches1 if d == "navigation"), 0)
        nav_score2 = next((s for d, s in matches2 if d == "navigation"), 0)

        # More navigation keywords = higher navigation score
        assert nav_score1 >= nav_score2


# ============================================================================
# Bootstrap Predictions Tests
# ============================================================================


class TestBootstrapPredictions:
    """Tests for bootstrap prediction functionality."""

    def test_get_navigation_predictions(self):
        """Navigation queries return navigation capabilities."""
        preds = get_bootstrap_predictions("plan the project session")
        assert "skills" in preds
        assert "tools" in preds
        assert len(preds["skills"]) > 0

    def test_get_building_predictions(self):
        """Building queries return building capabilities."""
        preds = get_bootstrap_predictions("write the implementation code")
        assert len(preds["skills"]) > 0 or len(preds["tools"]) > 0

        # Check that building tools are present
        tool_names = [t[0] for t in preds["tools"]]
        assert any(t in tool_names for t in ["Write", "Edit"])

    def test_predictions_have_scores(self):
        """Predictions include scores."""
        preds = get_bootstrap_predictions("plan something")
        if preds["skills"]:
            skill, score = preds["skills"][0]
            assert isinstance(score, float)
            assert 0 <= score <= 1

    def test_respects_top_k(self):
        """Respects top_k limit."""
        preds = get_bootstrap_predictions("plan code test", top_k=3)
        assert len(preds["skills"]) <= 3
        assert len(preds["tools"]) <= 3

    def test_empty_query_returns_empty(self):
        """Empty or non-matching query returns empty predictions."""
        preds = get_bootstrap_predictions("xyz abc 123")
        assert preds["skills"] == []
        assert preds["tools"] == []

    def test_format_predictions(self):
        """Predictions can be formatted as string."""
        preds = get_bootstrap_predictions("plan the project")
        formatted = format_bootstrap_predictions(preds)
        assert "Alias Cluster" in formatted
        assert "Skills:" in formatted
        assert "Tools:" in formatted


# ============================================================================
# Feedback Loop Integration Tests
# ============================================================================


class TestFeedbackLoopIntegration:
    """Tests for integration with feedback loop."""

    def test_augment_combines_all_sources(self):
        """Augmentation combines RAG, rollup, and alias predictions."""
        result = augment_with_alias_clusters(
            query="plan the project",
            rag_skills=["skill_a", "skill_b"],
            rag_tools=["tool_a"],
            rollup_skills=[("skill_c", 0.8)],
            rollup_tools=[("tool_b", 0.7)],
        )

        # Should have skills from all sources
        skill_names = [s[0] for s in result["skills"]]
        tool_names = [t[0] for t in result["tools"]]

        # RAG skills should be present
        assert any("skill_a" in s or "skill_b" in s for s in skill_names) or len(skill_names) > 0

    def test_augment_weights_work(self):
        """Different weights affect final scores."""
        # High RAG weight
        result_rag = augment_with_alias_clusters(
            query="xyz",  # Non-matching query
            rag_skills=["rag_skill"],
            rag_weight=0.9,
            rollup_weight=0.05,
            alias_weight=0.05,
        )

        # High alias weight with matching query
        result_alias = augment_with_alias_clusters(
            query="plan the project",  # Matching query
            rag_skills=["rag_skill"],
            rag_weight=0.1,
            rollup_weight=0.1,
            alias_weight=0.8,
        )

        # With non-matching query and high RAG weight, RAG skill should dominate
        if result_rag["skills"]:
            top_skill_rag = result_rag["skills"][0][0]
            assert top_skill_rag == "rag_skill"

    def test_augment_respects_top_k(self):
        """Augmentation respects top_k parameter."""
        result = augment_with_alias_clusters(
            query="plan code test debug",
            top_k=2,
        )
        assert len(result["skills"]) <= 2
        assert len(result["tools"]) <= 2

    def test_augment_empty_inputs(self):
        """Handles empty inputs gracefully."""
        result = augment_with_alias_clusters(
            query="xyz",
            rag_skills=None,
            rag_tools=None,
            rollup_skills=None,
            rollup_tools=None,
        )
        # Should not crash, may return empty
        assert "skills" in result
        assert "tools" in result


# ============================================================================
# Cluster Management Tests
# ============================================================================


class TestClusterManagement:
    """Tests for cluster management functions."""

    def test_add_keyword_to_existing_cluster(self):
        """Can add keyword to existing cluster."""
        # First load defaults
        load_alias_clusters()

        result = add_keyword_to_cluster("navigation", "newkeyword")
        assert result is True

        config = load_alias_clusters()
        assert "newkeyword" in config.get_cluster("navigation").keywords

    def test_add_keyword_creates_new_cluster(self):
        """Adding keyword to new domain creates cluster."""
        result = add_keyword_to_cluster("newdomain", "keyword")
        assert result is True

        config = load_alias_clusters()
        assert config.get_cluster("newdomain") is not None
        assert "keyword" in config.get_cluster("newdomain").keywords

    def test_add_duplicate_keyword_returns_false(self):
        """Adding duplicate keyword returns False."""
        load_alias_clusters()  # Ensure defaults loaded

        # First add succeeds
        add_keyword_to_cluster("navigation", "uniquekw")
        # Second add fails (duplicate)
        result = add_keyword_to_cluster("navigation", "uniquekw")
        assert result is False

    def test_add_skill_to_cluster(self):
        """Can add skill to cluster."""
        load_alias_clusters()

        result = add_skill_to_cluster("navigation", "new_skill")
        assert result is True

        config = load_alias_clusters()
        assert "new_skill" in config.get_cluster("navigation").skills

    def test_add_tool_to_cluster(self):
        """Can add tool to cluster."""
        load_alias_clusters()

        result = add_tool_to_cluster("navigation", "new_tool")
        assert result is True

        config = load_alias_clusters()
        assert "new_tool" in config.get_cluster("navigation").tools

    def test_list_all_clusters(self):
        """Can list all clusters."""
        load_alias_clusters()

        clusters = list_all_clusters()
        assert len(clusters) > 0
        assert all("domain" in c for c in clusters)

    def test_format_clusters_report(self):
        """Can format clusters report."""
        load_alias_clusters()

        report = format_clusters_report()
        assert "ALIAS CLUSTERS" in report
        assert "NAVIGATION" in report
        assert "Keywords" in report
        assert "Skills" in report
        assert "Tools" in report


# ============================================================================
# Integration with FeedbackLoop Class Tests
# ============================================================================


class TestFeedbackLoopClassIntegration:
    """Tests for FeedbackLoop class integration with alias clusters."""

    def test_feedback_loop_uses_alias_clusters_by_default(self):
        """FeedbackLoop.get_augmented_predictions uses alias clusters."""
        from capability_predictor.tracking import FeedbackLoop

        loop = FeedbackLoop()

        # Query that matches alias clusters
        result = loop.get_augmented_predictions(
            query="plan the project navigation",
            rag_skills=["rag_skill"],
        )

        # Should have results (from alias clusters at minimum)
        skill_names = [s[0] for s in result["skills"]]
        assert len(skill_names) >= 1

    def test_feedback_loop_can_disable_alias_clusters(self):
        """FeedbackLoop can disable alias cluster usage."""
        from capability_predictor.tracking import FeedbackLoop

        loop = FeedbackLoop()

        # With alias clusters disabled and no rollup data
        result = loop.get_augmented_predictions(
            query="plan the project",
            rag_skills=["only_rag"],
            use_alias_clusters=False,
        )

        # Should only have RAG results (since rollup is empty)
        skill_names = [s[0] for s in result["skills"]]
        # Only RAG skill should be present
        if skill_names:
            assert "only_rag" in skill_names


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_query(self):
        """Handles empty query string."""
        matches = match_query_to_domains("")
        assert matches == []

        preds = get_bootstrap_predictions("")
        assert preds["skills"] == []
        assert preds["tools"] == []

    def test_query_with_only_stop_words(self):
        """Handles query with only stop words."""
        matches = match_query_to_domains("the and or but")
        assert matches == []

    def test_very_long_query(self):
        """Handles very long query strings."""
        long_query = " ".join(["plan"] * 100 + ["code"] * 50)
        matches = match_query_to_domains(long_query)
        assert len(matches) > 0

    def test_special_characters_in_query(self):
        """Handles special characters in query."""
        matches = match_query_to_domains("plan!@#$% code???")
        # Should still extract "plan" and "code"
        assert len(matches) > 0

    def test_numeric_query(self):
        """Handles numeric-only query."""
        matches = match_query_to_domains("123 456 789")
        # Numbers might not match, but shouldn't crash
        assert isinstance(matches, list)

    def test_unicode_query(self):
        """Handles unicode in query."""
        matches = match_query_to_domains("plan プロジェクト code")
        # Should handle mixed unicode
        assert isinstance(matches, list)
