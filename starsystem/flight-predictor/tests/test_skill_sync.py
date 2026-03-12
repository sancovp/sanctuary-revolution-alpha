"""Tests for skill sync to Neo4j."""

import os
import pytest
from unittest.mock import MagicMock, patch

# Import the module under test
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync.sync_skills_to_neo4j import (
    create_skill_schema,
    sync_skill_to_neo4j,
    sync_skillset_to_neo4j,
    load_skills_from_skillmanager,
    load_skillsets_from_skillmanager,
)


class TestSkillSchema:
    """Test skill graph schema creation."""

    def test_create_skill_schema_queries(self):
        """Test that schema creation runs expected queries."""
        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        result = create_skill_schema(mock_driver)

        # Verify schema was created
        assert result["schema_created"] is True
        assert len(result["results"]) == 6  # 3 constraints + 3 indexes

        # Verify all queries were run
        run_calls = mock_session.run.call_args_list
        queries_run = [call[0][0] for call in run_calls]

        # Check constraints exist
        assert any("Skill" in q and "UNIQUE" in q for q in queries_run)
        assert any("Skillset" in q and "UNIQUE" in q for q in queries_run)
        assert any("SkillDomain" in q and "UNIQUE" in q for q in queries_run)

        # Check indexes exist
        assert any("skill_domain_idx" in q for q in queries_run)
        assert any("skill_category_idx" in q for q in queries_run)


class TestSkillSync:
    """Test syncing skills to Neo4j."""

    def test_sync_skill_creates_node_and_domain(self):
        """Test that syncing a skill creates both skill and domain nodes."""
        mock_session = MagicMock()
        mock_record = {"skill_name": "test-skill", "domain_name": "paiab"}
        mock_result = MagicMock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        skill_data = {
            "name": "test-skill",
            "domain": "paiab",
            "subdomain": "mcp",
            "category": "preflight",
            "description": "Test skill description",
            "what": "Test what",
            "when": "Test when"
        }

        result = sync_skill_to_neo4j(mock_driver, skill_data)

        assert result["skill"] == "test-skill"
        assert result["domain"] == "paiab"
        assert result["status"] == "synced"

        # Verify the query was called
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "MERGE (s:Skill" in call_args[0][0]
        assert "MERGE (d:SkillDomain" in call_args[0][0]
        assert "MERGE (s)-[:BELONGS_TO]->(d)" in call_args[0][0]


class TestSkillsetSync:
    """Test syncing skillsets to Neo4j."""

    def test_sync_skillset_creates_node_and_links(self):
        """Test that syncing a skillset creates node and links skills."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"skill_name": "skill1", "skillset_name": "test-set"}
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        skillset_data = {
            "name": "test-set",
            "domain": "paiab",
            "subdomain": "",
            "description": "Test skillset",
            "skills": ["skill1", "skill2"]
        }

        result = sync_skillset_to_neo4j(mock_driver, skillset_data)

        assert result["skillset"] == "test-set"
        assert result["domain"] == "paiab"
        assert result["status"] == "synced"

        # Verify multiple calls: 1 for create + 2 for linking skills
        assert mock_session.run.call_count == 3


class TestLoadFromSkillmanager:
    """Test loading skills from skillmanager directory."""

    @patch("sync.sync_skills_to_neo4j.Path")
    def test_load_skills_parses_metadata(self, mock_path):
        """Test that skills are loaded with correct metadata."""
        # Mock the directory structure
        mock_skills_path = MagicMock()
        mock_path.return_value = mock_skills_path
        mock_skills_path.exists.return_value = True

        # Mock a skill directory
        mock_skill_dir = MagicMock()
        mock_skill_dir.name = "test-skill"
        mock_skill_dir.is_dir.return_value = True

        # Mock metadata file
        mock_metadata = MagicMock()
        mock_metadata.exists.return_value = True
        mock_metadata.read_text.return_value = '{"domain": "paiab", "category": "preflight", "what": "test", "when": "always"}'

        # Mock SKILL.md
        mock_skill_md = MagicMock()
        mock_skill_md.exists.return_value = False

        mock_skill_dir.__truediv__ = MagicMock(side_effect=lambda x: mock_metadata if x == "_metadata.json" else mock_skill_md)
        mock_skills_path.iterdir.return_value = [mock_skill_dir]

        skills = load_skills_from_skillmanager("/fake/path")

        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
        assert skills[0]["domain"] == "paiab"
        assert skills[0]["category"] == "preflight"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
