"""
Tests for the capability_predictor.tracking module.

Tests cover:
- TrackingSession creation and updates
- Session persistence (save/load)
- Active session management
- Observation storage
- Mismatch report formatting
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from capability_predictor.tracking import (
    TrackingSession,
    clear_active_session,
    end_tracking_session,
    format_mismatch_report,
    get_active_session,
    get_observations_dir,
    get_sessions_dir,
    get_storage_dir,
    load_all_observations,
    load_session,
    record_tool_from_hook,
    save_observation,
    save_session,
    set_active_session,
    start_tracking_session,
)
from capability_predictor.models import ActualUsage


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Use a temporary directory for all storage operations."""
    with patch.dict(os.environ, {"CAPABILITY_TRACKER_DIR": str(tmp_path)}):
        yield tmp_path


class TestTrackingSession:
    """Tests for TrackingSession class."""

    def test_create_session_with_defaults(self):
        """Test creating a session with default values."""
        session = TrackingSession()
        assert session.session_id is not None
        assert len(session.session_id) == 8  # UUID[:8]
        assert session.step_description == ""
        assert session.predicted_skills == []
        assert session.predicted_tools == []
        assert session.actual_skills == []
        assert session.actual_tools == []

    def test_create_session_with_values(self):
        """Test creating a session with provided values."""
        session = TrackingSession(
            session_id="test123",
            step_description="Implement feature X",
            predicted_skills=["make-skill", "understand-skills"],
            predicted_tools=["Edit", "Write", "Bash"],
        )
        assert session.session_id == "test123"
        assert session.step_description == "Implement feature X"
        assert session.predicted_skills == ["make-skill", "understand-skills"]
        assert session.predicted_tools == ["Edit", "Write", "Bash"]

    def test_record_tool_use(self):
        """Test recording tool usage."""
        session = TrackingSession()
        session.record_tool_use("Edit", {"file_path": "/test.py"})
        session.record_tool_use("Write", {"file_path": "/new.py"})

        assert "Edit" in session.actual_tools
        assert "Write" in session.actual_tools
        assert len(session.tool_events) == 2

    def test_record_tool_use_no_duplicates(self):
        """Test that duplicate tool names aren't added."""
        session = TrackingSession()
        session.record_tool_use("Edit")
        session.record_tool_use("Edit")
        session.record_tool_use("Edit")

        assert session.actual_tools == ["Edit"]
        assert len(session.tool_events) == 3  # Events still logged

    def test_record_skill_use(self):
        """Test recording skill usage."""
        session = TrackingSession()
        session.record_skill_use("make-mcp")
        session.record_skill_use("understand-skills")

        assert "make-mcp" in session.actual_skills
        assert "understand-skills" in session.actual_skills

    def test_to_actual_usage(self):
        """Test conversion to ActualUsage model."""
        session = TrackingSession(
            session_id="test123",
            step_description="Test step",
            predicted_skills=["skill-a", "skill-b"],
            predicted_tools=["Edit", "Write"],
        )
        session.actual_skills = ["skill-a", "skill-c"]
        session.actual_tools = ["Edit", "Bash"]

        usage = session.to_actual_usage()

        assert isinstance(usage, ActualUsage)
        assert usage.session_id == "test123"
        assert usage.skill_true_positives == ["skill-a"]
        assert usage.skill_false_positives == ["skill-b"]
        assert usage.skill_false_negatives == ["skill-c"]
        assert usage.tool_true_positives == ["Edit"]
        assert usage.tool_false_positives == ["Write"]
        assert usage.tool_false_negatives == ["Bash"]

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        session = TrackingSession(
            session_id="test123",
            step_description="Test step",
            predicted_skills=["skill-a"],
            predicted_tools=["Edit"],
        )
        session.record_tool_use("Bash")
        session.record_skill_use("skill-b")

        data = session.to_dict()
        restored = TrackingSession.from_dict(data)

        assert restored.session_id == session.session_id
        assert restored.step_description == session.step_description
        assert restored.predicted_skills == session.predicted_skills
        assert restored.predicted_tools == session.predicted_tools
        assert restored.actual_skills == session.actual_skills
        assert restored.actual_tools == session.actual_tools


class TestSessionPersistence:
    """Tests for session save/load functionality."""

    def test_save_and_load_session(self, temp_storage_dir):
        """Test saving and loading a session."""
        session = TrackingSession(
            session_id="persist1",
            step_description="Test persistence",
        )
        session.record_tool_use("Edit")

        # Save
        filepath = save_session(session)
        assert filepath.exists()
        assert filepath.name == "persist1.json"

        # Load
        loaded = load_session("persist1")
        assert loaded is not None
        assert loaded.session_id == "persist1"
        assert "Edit" in loaded.actual_tools

    def test_load_nonexistent_session(self, temp_storage_dir):
        """Test loading a session that doesn't exist."""
        loaded = load_session("nonexistent")
        assert loaded is None

    def test_get_storage_dir_creates_directory(self, temp_storage_dir):
        """Test that get_storage_dir creates the directory."""
        storage_dir = get_storage_dir()
        assert storage_dir.exists()
        assert storage_dir.is_dir()

    def test_get_sessions_dir_creates_directory(self, temp_storage_dir):
        """Test that get_sessions_dir creates the directory."""
        sessions_dir = get_sessions_dir()
        assert sessions_dir.exists()
        assert sessions_dir.name == "sessions"


class TestActiveSession:
    """Tests for active session management."""

    def test_set_and_get_active_session(self, temp_storage_dir):
        """Test setting and getting the active session."""
        session = TrackingSession(session_id="active1")

        set_active_session(session)
        retrieved = get_active_session()

        assert retrieved is not None
        assert retrieved.session_id == "active1"

    def test_get_active_session_when_none(self, temp_storage_dir):
        """Test getting active session when none is set."""
        result = get_active_session()
        assert result is None

    def test_clear_active_session(self, temp_storage_dir):
        """Test clearing the active session."""
        session = TrackingSession(session_id="to_clear")
        set_active_session(session)

        # Verify it's set
        assert get_active_session() is not None

        # Clear it
        clear_active_session()

        # Verify it's cleared
        assert get_active_session() is None


class TestObservationStorage:
    """Tests for observation (completed session) storage."""

    def test_save_observation(self, temp_storage_dir):
        """Test saving an observation."""
        usage = ActualUsage(
            session_id="obs1",
            step_description="Test observation",
            predicted_skills=["skill-a"],
            predicted_tools=["Edit"],
            actual_skills=["skill-b"],
            actual_tools=["Edit", "Bash"],
        )

        filepath = save_observation(usage)

        assert filepath.exists()
        assert "obs1" in filepath.name

        # Verify content
        data = json.loads(filepath.read_text())
        assert data["session_id"] == "obs1"
        assert "analysis" in data
        assert data["analysis"]["tool_true_positives"] == ["Edit"]

    def test_load_all_observations(self, temp_storage_dir):
        """Test loading all observations."""
        # Save multiple observations
        for i in range(3):
            usage = ActualUsage(
                session_id=f"obs{i}",
                step_description=f"Test {i}",
            )
            save_observation(usage)

        observations = load_all_observations()
        assert len(observations) == 3


class TestHookIntegration:
    """Tests for hook integration functions."""

    def test_record_tool_from_hook_with_active_session(self, temp_storage_dir):
        """Test recording tool from hook with active session."""
        session = start_tracking_session(
            step_description="Hook test",
            predicted_tools=["Edit"],
        )

        result = record_tool_from_hook("Bash", {"command": "ls"})

        assert result is True

        # Verify it was recorded
        updated = get_active_session()
        assert "Bash" in updated.actual_tools

    def test_record_tool_from_hook_without_active_session(self, temp_storage_dir):
        """Test recording tool from hook without active session."""
        clear_active_session()

        result = record_tool_from_hook("Bash")

        assert result is False

    def test_start_and_end_tracking_session(self, temp_storage_dir):
        """Test the full session lifecycle."""
        # Start session with predictions
        session = start_tracking_session(
            step_description="Full lifecycle test",
            predicted_skills=["make-mcp"],
            predicted_tools=["Edit", "Write"],
        )

        assert session is not None
        assert get_active_session() is not None

        # Simulate some tool use
        record_tool_from_hook("Edit")
        record_tool_from_hook("Bash")

        # End session
        usage = end_tracking_session()

        assert usage is not None
        assert usage.tool_true_positives == ["Edit"]
        assert usage.tool_false_positives == ["Write"]
        assert usage.tool_false_negatives == ["Bash"]

        # Verify session is cleared
        assert get_active_session() is None

        # Verify observation was saved
        observations = load_all_observations()
        assert len(observations) == 1


class TestMismatchReport:
    """Tests for mismatch report formatting."""

    def test_format_mismatch_report_basic(self):
        """Test basic mismatch report formatting."""
        usage = ActualUsage(
            session_id="report1",
            step_description="Test step",
            predicted_skills=["skill-a", "skill-b"],
            predicted_tools=["Edit", "Write"],
            actual_skills=["skill-a", "skill-c"],
            actual_tools=["Edit", "Bash"],
        )

        report = format_mismatch_report(usage)

        assert "report1" in report
        assert "Test step" in report
        assert "skill-a" in report  # True positive
        assert "skill-b" in report  # False positive
        assert "skill-c" in report  # False negative
        assert "Edit" in report  # True positive
        assert "Write" in report  # False positive
        assert "Bash" in report  # False negative

    def test_format_mismatch_report_empty(self):
        """Test mismatch report with no predictions or actuals."""
        usage = ActualUsage(
            session_id="empty",
            step_description="",
        )

        report = format_mismatch_report(usage)

        assert "(none)" in report
        assert "(no description)" in report


# ============================================================================
# Rollup Aggregation Tests (Phase 3.3)
# ============================================================================


from capability_predictor.tracking import (
    CapabilityRollup,
    compute_rollup,
    extract_keywords,
    format_rollup_report,
    get_rollup_file,
    load_rollup,
    save_rollup,
    # Mismatch detection (Phase 3.4)
    MismatchAnalysis,
    compute_mismatch_analysis,
    get_improvement_suggestions,
    format_mismatch_analysis_report,
)


class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_basic_extraction(self):
        """Test extracting keywords from simple text."""
        keywords = extract_keywords("Plan the project structure")
        assert "plan" in keywords
        assert "project" in keywords
        assert "structure" in keywords

    def test_stop_words_removed(self):
        """Test that stop words are filtered out."""
        keywords = extract_keywords("This is a test of the system")
        assert "the" not in keywords
        assert "is" not in keywords
        assert "a" not in keywords
        assert "test" in keywords
        assert "system" in keywords

    def test_short_words_removed(self):
        """Test that very short words are filtered."""
        keywords = extract_keywords("I am testing")
        assert "am" not in keywords
        assert "testing" in keywords

    def test_lowercase_normalization(self):
        """Test that keywords are lowercased."""
        keywords = extract_keywords("Write TESTS for Code")
        assert "write" in keywords
        assert "tests" in keywords
        assert "code" in keywords
        assert "TESTS" not in keywords

    def test_empty_string(self):
        """Test handling of empty string."""
        keywords = extract_keywords("")
        assert keywords == []

    def test_only_stop_words(self):
        """Test string with only stop words."""
        keywords = extract_keywords("the a an is are")
        assert keywords == []


class TestCapabilityRollup:
    """Tests for CapabilityRollup class."""

    def test_create_empty_rollup(self):
        """Test creating an empty rollup."""
        rollup = CapabilityRollup()
        assert rollup.total_observations == 0
        assert rollup.skill_counts == {}
        assert rollup.tool_counts == {}

    def test_add_single_observation(self):
        """Test adding a single observation."""
        rollup = CapabilityRollup()
        rollup.add_observation({
            "step_description": "Plan the feature",
            "actual_skills": ["starlog", "waypoint"],
            "actual_tools": ["Read", "Edit"],
        })

        assert rollup.total_observations == 1
        assert "plan" in rollup.keyword_observations
        assert "feature" in rollup.keyword_observations

    def test_add_multiple_observations(self):
        """Test adding multiple observations."""
        rollup = CapabilityRollup()

        # First observation
        rollup.add_observation({
            "step_description": "Plan the feature",
            "actual_skills": ["starlog"],
            "actual_tools": ["Read"],
        })

        # Second observation with same keyword
        rollup.add_observation({
            "step_description": "Plan the implementation",
            "actual_skills": ["starlog", "waypoint"],
            "actual_tools": ["Edit"],
        })

        assert rollup.total_observations == 2
        assert rollup.keyword_observations["plan"] == 2
        assert rollup.skill_counts["plan"]["starlog"] == 2
        assert rollup.skill_counts["plan"]["waypoint"] == 1

    def test_get_skill_probabilities(self):
        """Test skill probability calculation."""
        rollup = CapabilityRollup()

        # Add observations for "plan" keyword
        rollup.add_observation({
            "step_description": "Plan the feature",
            "actual_skills": ["starlog"],
            "actual_tools": [],
        })
        rollup.add_observation({
            "step_description": "Plan the structure",
            "actual_skills": ["starlog", "waypoint"],
            "actual_tools": [],
        })

        probs = rollup.get_skill_probabilities("plan")

        # starlog appears in 2/2 = 100%
        # waypoint appears in 1/2 = 50%
        assert len(probs) == 2
        assert probs[0] == ("starlog", 1.0)  # First (highest)
        assert probs[1] == ("waypoint", 0.5)

    def test_get_tool_probabilities(self):
        """Test tool probability calculation."""
        rollup = CapabilityRollup()

        rollup.add_observation({
            "step_description": "Write the code",
            "actual_skills": [],
            "actual_tools": ["Edit", "Write"],
        })
        rollup.add_observation({
            "step_description": "Write the tests",
            "actual_skills": [],
            "actual_tools": ["Edit", "Bash"],
        })

        probs = rollup.get_tool_probabilities("write")

        # Edit appears in 2/2 = 100%
        assert any(t == "Edit" and p == 1.0 for t, p in probs)
        assert any(t == "Write" and p == 0.5 for t, p in probs)
        assert any(t == "Bash" and p == 0.5 for t, p in probs)

    def test_get_probabilities_for_unknown_keyword(self):
        """Test getting probabilities for unknown keyword."""
        rollup = CapabilityRollup()
        assert rollup.get_skill_probabilities("unknown") == []
        assert rollup.get_tool_probabilities("unknown") == []

    def test_get_aggregated_predictions(self):
        """Test aggregated predictions from multiple keywords."""
        rollup = CapabilityRollup()

        # Build up some patterns
        rollup.add_observation({
            "step_description": "Plan the feature",
            "actual_skills": ["starlog"],
            "actual_tools": ["Read"],
        })
        rollup.add_observation({
            "step_description": "Implement the feature",
            "actual_skills": ["make-mcp"],
            "actual_tools": ["Edit", "Write"],
        })
        rollup.add_observation({
            "step_description": "Plan implementation",
            "actual_skills": ["starlog", "waypoint"],
            "actual_tools": ["Read"],
        })

        # Query that contains multiple keywords
        preds = rollup.get_aggregated_predictions("Plan feature implementation")

        assert "skills" in preds
        assert "tools" in preds
        assert len(preds["skills"]) > 0
        assert len(preds["tools"]) > 0

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        rollup = CapabilityRollup()
        rollup.add_observation({
            "step_description": "Test the feature",
            "actual_skills": ["test-skill"],
            "actual_tools": ["Bash"],
        })

        data = rollup.to_dict()
        restored = CapabilityRollup.from_dict(data)

        assert restored.total_observations == rollup.total_observations
        assert restored.skill_counts == rollup.skill_counts
        assert restored.tool_counts == rollup.tool_counts
        assert restored.keyword_observations == rollup.keyword_observations

    def test_observation_without_keywords_ignored(self):
        """Test that observations without extractable keywords are ignored."""
        rollup = CapabilityRollup()
        rollup.add_observation({
            "step_description": "a an the",  # Only stop words
            "actual_skills": ["skill-a"],
            "actual_tools": ["Tool-A"],
        })

        assert rollup.total_observations == 0


class TestRollupPersistence:
    """Tests for rollup save/load functionality."""

    def test_save_and_load_rollup(self, temp_storage_dir):
        """Test saving and loading a rollup."""
        rollup = CapabilityRollup()
        rollup.add_observation({
            "step_description": "Test persistence",
            "actual_skills": ["persist-skill"],
            "actual_tools": ["Persist-Tool"],
        })

        # Save
        filepath = save_rollup(rollup)
        assert filepath.exists()

        # Load
        loaded = load_rollup()
        assert loaded is not None
        assert loaded.total_observations == 1
        assert "test" in loaded.keyword_observations

    def test_load_nonexistent_rollup(self, temp_storage_dir):
        """Test loading when no rollup exists."""
        loaded = load_rollup()
        assert loaded is None

    def test_compute_rollup_from_observations(self, temp_storage_dir):
        """Test computing rollup from stored observations."""
        # First, create some observations
        for i in range(3):
            usage = ActualUsage(
                session_id=f"rollup{i}",
                step_description=f"Test step {i} with planning",
                actual_skills=["planning-skill"],
                actual_tools=["Edit"],
            )
            save_observation(usage)

        # Compute rollup
        rollup = compute_rollup()

        assert rollup.total_observations == 3
        assert "test" in rollup.keyword_observations
        assert "planning" in rollup.keyword_observations

        # Verify it was saved
        loaded = load_rollup()
        assert loaded is not None
        assert loaded.total_observations == 3


class TestFormatRollupReport:
    """Tests for rollup report formatting."""

    def test_format_empty_rollup(self):
        """Test formatting an empty rollup."""
        rollup = CapabilityRollup()
        report = format_rollup_report(rollup)

        assert "Total Observations: 0" in report
        assert "No keyword patterns recorded yet" in report

    def test_format_populated_rollup(self):
        """Test formatting a rollup with data."""
        rollup = CapabilityRollup()
        rollup.add_observation({
            "step_description": "Plan the feature implementation",
            "actual_skills": ["starlog", "waypoint"],
            "actual_tools": ["Read", "Edit"],
        })
        rollup.add_observation({
            "step_description": "Plan the testing strategy",
            "actual_skills": ["starlog"],
            "actual_tools": ["Bash"],
        })

        report = format_rollup_report(rollup)

        assert "Total Observations: 2" in report
        assert "plan" in report.lower()
        assert "starlog" in report
        # Should show percentages
        assert "%" in report


# ============================================================================
# Mismatch Detection Tests (Phase 3.4)
# ============================================================================


class TestMismatchAnalysis:
    """Tests for MismatchAnalysis class."""

    def test_create_empty_analysis(self):
        """Test creating an empty analysis."""
        analysis = MismatchAnalysis()
        assert analysis.total_observations == 0
        assert analysis.skill_true_positives == 0
        assert analysis.tool_true_positives == 0

    def test_add_single_observation(self):
        """Test adding a single observation."""
        analysis = MismatchAnalysis()
        analysis.add_observation({
            "analysis": {
                "skill_true_positives": ["skill-a"],
                "skill_false_positives": ["skill-b"],
                "skill_false_negatives": ["skill-c"],
                "tool_true_positives": ["Edit"],
                "tool_false_positives": ["Write"],
                "tool_false_negatives": ["Bash"],
            }
        })

        assert analysis.total_observations == 1
        assert analysis.skill_true_positives == 1
        assert analysis.skill_false_positives == 1
        assert analysis.skill_false_negatives == 1
        assert analysis.tool_true_positives == 1
        assert analysis.tool_false_positives == 1
        assert analysis.tool_false_negatives == 1

    def test_add_multiple_observations(self):
        """Test adding multiple observations."""
        analysis = MismatchAnalysis()

        # First observation
        analysis.add_observation({
            "analysis": {
                "skill_true_positives": ["skill-a"],
                "skill_false_positives": [],
                "skill_false_negatives": ["skill-b"],
                "tool_true_positives": ["Edit", "Read"],
                "tool_false_positives": [],
                "tool_false_negatives": [],
            }
        })

        # Second observation
        analysis.add_observation({
            "analysis": {
                "skill_true_positives": ["skill-a", "skill-c"],
                "skill_false_positives": ["skill-d"],
                "skill_false_negatives": [],
                "tool_true_positives": ["Edit"],
                "tool_false_positives": ["Write"],
                "tool_false_negatives": ["Bash"],
            }
        })

        assert analysis.total_observations == 2
        assert analysis.skill_true_positives == 3  # 1 + 2
        assert analysis.skill_false_positives == 1
        assert analysis.skill_false_negatives == 1
        assert analysis.skill_hits["skill-a"] == 2  # appeared twice

    def test_precision_calculation(self):
        """Test precision calculation."""
        analysis = MismatchAnalysis()
        analysis.skill_true_positives = 8
        analysis.skill_false_positives = 2
        # precision = 8 / (8 + 2) = 0.8
        assert analysis.skill_precision == 0.8

    def test_recall_calculation(self):
        """Test recall calculation."""
        analysis = MismatchAnalysis()
        analysis.skill_true_positives = 6
        analysis.skill_false_negatives = 4
        # recall = 6 / (6 + 4) = 0.6
        assert analysis.skill_recall == 0.6

    def test_f1_calculation(self):
        """Test F1 score calculation."""
        analysis = MismatchAnalysis()
        analysis.skill_true_positives = 8
        analysis.skill_false_positives = 2
        analysis.skill_false_negatives = 2
        # precision = 0.8, recall = 0.8
        # f1 = 2 * (0.8 * 0.8) / (0.8 + 0.8) = 0.8
        assert abs(analysis.skill_f1 - 0.8) < 0.001

    def test_precision_zero_division(self):
        """Test precision with no predictions."""
        analysis = MismatchAnalysis()
        assert analysis.skill_precision == 0.0

    def test_recall_zero_division(self):
        """Test recall with no actual usage."""
        analysis = MismatchAnalysis()
        assert analysis.skill_recall == 0.0

    def test_f1_zero_division(self):
        """Test F1 with no data."""
        analysis = MismatchAnalysis()
        assert analysis.skill_f1 == 0.0

    def test_tool_metrics(self):
        """Test tool precision/recall/F1."""
        analysis = MismatchAnalysis()
        analysis.tool_true_positives = 10
        analysis.tool_false_positives = 5
        analysis.tool_false_negatives = 5

        assert analysis.tool_precision == 10 / 15  # 10 / (10 + 5)
        assert analysis.tool_recall == 10 / 15  # 10 / (10 + 5)
        # f1 = 2 * (2/3 * 2/3) / (2/3 + 2/3) = 2/3
        assert abs(analysis.tool_f1 - (2/3)) < 0.001

    def test_to_dict(self):
        """Test serialization to dict."""
        analysis = MismatchAnalysis()
        analysis.add_observation({
            "analysis": {
                "skill_true_positives": ["skill-a"],
                "skill_false_positives": ["skill-b"],
                "skill_false_negatives": ["skill-c"],
                "tool_true_positives": ["Edit"],
                "tool_false_positives": [],
                "tool_false_negatives": ["Bash"],
            }
        })

        data = analysis.to_dict()

        assert "total_observations" in data
        assert "skills" in data
        assert "tools" in data
        assert data["skills"]["true_positives"] == 1
        assert data["skills"]["precision"] == 0.5  # 1 / (1 + 1)
        assert "top_misses" in data["skills"]

    def test_tracks_individual_misses(self):
        """Test tracking of individual skill/tool misses."""
        analysis = MismatchAnalysis()

        # Multiple observations with same miss
        for _ in range(3):
            analysis.add_observation({
                "analysis": {
                    "skill_true_positives": [],
                    "skill_false_positives": [],
                    "skill_false_negatives": ["common-miss"],
                    "tool_true_positives": [],
                    "tool_false_positives": [],
                    "tool_false_negatives": ["Bash"],
                }
            })

        assert analysis.skill_misses["common-miss"] == 3
        assert analysis.tool_misses["Bash"] == 3

    def test_tracks_over_predictions(self):
        """Test tracking of over-predictions."""
        analysis = MismatchAnalysis()

        for _ in range(2):
            analysis.add_observation({
                "analysis": {
                    "skill_true_positives": [],
                    "skill_false_positives": ["over-predicted-skill"],
                    "skill_false_negatives": [],
                    "tool_true_positives": [],
                    "tool_false_positives": ["Write"],
                    "tool_false_negatives": [],
                }
            })

        assert analysis.skill_over_predictions["over-predicted-skill"] == 2
        assert analysis.tool_over_predictions["Write"] == 2


class TestComputeMismatchAnalysis:
    """Tests for compute_mismatch_analysis function."""

    def test_compute_from_observations(self, temp_storage_dir):
        """Test computing analysis from stored observations."""
        # Create some observations
        for i in range(3):
            usage = ActualUsage(
                session_id=f"mismatch{i}",
                step_description=f"Test step {i}",
                predicted_skills=["skill-a", "skill-b"],
                predicted_tools=["Edit"],
                actual_skills=["skill-a", "skill-c"],
                actual_tools=["Edit", "Bash"],
            )
            save_observation(usage)

        # Compute analysis
        analysis = compute_mismatch_analysis()

        assert analysis.total_observations == 3
        # skill-a is TP in all 3 observations
        assert analysis.skill_true_positives == 3
        # skill-b is FP in all 3 observations
        assert analysis.skill_false_positives == 3
        # skill-c is FN in all 3 observations
        assert analysis.skill_false_negatives == 3

    def test_empty_observations(self, temp_storage_dir):
        """Test computing analysis with no observations."""
        analysis = compute_mismatch_analysis()
        assert analysis.total_observations == 0


class TestGetImprovementSuggestions:
    """Tests for get_improvement_suggestions function."""

    def test_no_observations(self):
        """Test suggestions with no observations."""
        analysis = MismatchAnalysis()
        suggestions = get_improvement_suggestions(analysis)

        assert len(suggestions) == 1
        assert "No observations recorded" in suggestions[0]

    def test_skill_misses_suggestion(self):
        """Test suggestions for skill misses."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_false_negatives = 3
        analysis.skill_misses = {"missed-skill-1": 2, "missed-skill-2": 1}

        suggestions = get_improvement_suggestions(analysis)

        assert any("SKILL MISSES" in s for s in suggestions)
        assert any("missed-skill-1" in s for s in suggestions)

    def test_skill_over_predictions_suggestion(self):
        """Test suggestions for skill over-predictions."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_false_positives = 2
        analysis.skill_over_predictions = {"over-skill": 2}

        suggestions = get_improvement_suggestions(analysis)

        assert any("SKILL OVER-PREDICTIONS" in s for s in suggestions)
        assert any("over-skill" in s for s in suggestions)

    def test_tool_misses_suggestion(self):
        """Test suggestions for tool misses."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.tool_false_negatives = 2
        analysis.tool_misses = {"Bash": 2}

        suggestions = get_improvement_suggestions(analysis)

        assert any("TOOL MISSES" in s for s in suggestions)
        assert any("Bash" in s for s in suggestions)

    def test_low_precision_suggestion(self):
        """Test suggestion for low precision."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_true_positives = 2
        analysis.skill_false_positives = 8  # precision = 2/10 = 20%

        suggestions = get_improvement_suggestions(analysis)

        assert any("precision is low" in s.lower() for s in suggestions)

    def test_low_recall_suggestion(self):
        """Test suggestion for low recall."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_true_positives = 2
        analysis.skill_false_negatives = 8  # recall = 2/10 = 20%

        suggestions = get_improvement_suggestions(analysis)

        assert any("recall is low" in s.lower() for s in suggestions)

    def test_good_quality_suggestion(self):
        """Test suggestion when quality is good."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_true_positives = 10
        analysis.skill_false_positives = 0
        analysis.skill_false_negatives = 0
        analysis.tool_true_positives = 10
        analysis.tool_false_positives = 0
        analysis.tool_false_negatives = 0

        suggestions = get_improvement_suggestions(analysis)

        assert any("quality is good" in s.lower() for s in suggestions)


class TestFormatMismatchAnalysisReport:
    """Tests for format_mismatch_analysis_report function."""

    def test_empty_report(self):
        """Test formatting empty analysis."""
        analysis = MismatchAnalysis()
        report = format_mismatch_analysis_report(analysis)

        assert "Total Observations Analyzed: 0" in report
        assert "No observations recorded" in report

    def test_report_contains_metrics(self):
        """Test that report contains all metrics."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 5
        analysis.skill_true_positives = 10
        analysis.skill_false_positives = 2
        analysis.skill_false_negatives = 3
        analysis.tool_true_positives = 15
        analysis.tool_false_positives = 3
        analysis.tool_false_negatives = 2

        report = format_mismatch_analysis_report(analysis)

        # Check structure
        assert "SKILL PREDICTIONS" in report
        assert "TOOL PREDICTIONS" in report
        assert "IMPROVEMENT SUGGESTIONS" in report

        # Check metrics present
        assert "True Positives" in report
        assert "False Positives" in report
        assert "False Negatives" in report
        assert "Precision" in report
        assert "Recall" in report
        assert "F1 Score" in report

    def test_report_shows_misses(self):
        """Test that report shows top misses."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_misses = {"missed-skill": 3}
        analysis.skill_false_negatives = 3

        report = format_mismatch_analysis_report(analysis)

        assert "missed-skill" in report
        assert "LEARN these mappings" in report

    def test_report_shows_over_predictions(self):
        """Test that report shows over-predictions."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_over_predictions = {"over-skill": 2}
        analysis.skill_false_positives = 2

        report = format_mismatch_analysis_report(analysis)

        assert "over-skill" in report
        assert "REDUCE these weights" in report

    def test_report_includes_suggestions(self):
        """Test that report includes improvement suggestions."""
        analysis = MismatchAnalysis()
        analysis.total_observations = 1
        analysis.skill_true_positives = 2
        analysis.skill_false_negatives = 8
        analysis.skill_misses = {"missed": 8}

        report = format_mismatch_analysis_report(analysis)

        assert "IMPROVEMENT SUGGESTIONS" in report
        # Should have suggestion about low recall
        assert "recall" in report.lower()


# ============================================================================
# Feedback Loop Integration Tests (Phase 4.1)
# ============================================================================


from capability_predictor.tracking import (
    FeedbackLoop,
    get_feedback_loop,
    augment_predictions_with_feedback,
)


class TestFeedbackLoop:
    """Tests for FeedbackLoop class."""

    def test_create_feedback_loop(self, temp_storage_dir):
        """Test creating a feedback loop."""
        loop = FeedbackLoop()
        assert loop._rollup is None  # Lazy loading

    def test_rollup_lazy_loading(self, temp_storage_dir):
        """Test that rollup is loaded lazily."""
        loop = FeedbackLoop()

        # Access rollup property
        rollup = loop.rollup

        assert rollup is not None
        assert rollup.total_observations == 0  # Fresh rollup

    def test_rollup_loads_existing_data(self, temp_storage_dir):
        """Test that rollup loads existing data from disk."""
        # First, create a rollup with data
        existing_rollup = CapabilityRollup()
        existing_rollup.add_observation({
            "step_description": "Test the feature",
            "actual_skills": ["test-skill"],
            "actual_tools": ["Bash"],
        })
        save_rollup(existing_rollup)

        # Now create a new FeedbackLoop - it should load existing data
        loop = FeedbackLoop()
        assert loop.rollup.total_observations == 1

    def test_get_augmented_predictions_empty_rollup(self, temp_storage_dir):
        """Test augmented predictions with empty rollup (alias clusters disabled)."""
        loop = FeedbackLoop()

        # With only RAG predictions, no rollup data, alias clusters disabled
        result = loop.get_augmented_predictions(
            query="Plan the feature",
            rag_skills=["starlog", "waypoint"],
            rag_tools=["Edit", "Write"],
            use_alias_clusters=False,  # Disable alias clusters for this test
        )

        assert "skills" in result
        assert "tools" in result
        # Should have only the RAG skills/tools with weighted scores
        assert len(result["skills"]) == 2
        assert len(result["tools"]) == 2

    def test_get_augmented_predictions_with_alias_clusters(self, temp_storage_dir):
        """Test augmented predictions with alias clusters enabled."""
        loop = FeedbackLoop()

        # With RAG predictions and alias clusters enabled (default)
        result = loop.get_augmented_predictions(
            query="Plan the project navigation",  # Matches navigation alias cluster
            rag_skills=["starlog"],
            rag_tools=["Edit"],
        )

        assert "skills" in result
        assert "tools" in result
        # Should have more than just RAG predictions due to alias clusters
        skill_names = [s[0] for s in result["skills"]]
        # Alias clusters should add navigation-related skills
        assert len(skill_names) >= 1

    def test_get_augmented_predictions_with_rollup_data(self, temp_storage_dir):
        """Test augmented predictions with rollup data."""
        loop = FeedbackLoop()

        # Add some observations to rollup
        loop.rollup.add_observation({
            "step_description": "Plan the implementation",
            "actual_skills": ["flight-config"],
            "actual_tools": ["Read"],
        })
        loop.rollup.add_observation({
            "step_description": "Plan the structure",
            "actual_skills": ["flight-config", "starlog"],
            "actual_tools": ["Read", "Glob"],
        })

        # Now get predictions for similar query
        result = loop.get_augmented_predictions(
            query="Plan the feature",
            rag_skills=["starlog", "waypoint"],
            rag_tools=["Edit", "Write"],
        )

        # Should include rollup-learned patterns
        skill_names = [s[0] for s in result["skills"]]
        tool_names = [t[0] for t in result["tools"]]

        # flight-config should appear from rollup
        assert "flight-config" in skill_names
        # Read should appear from rollup
        assert "Read" in tool_names

    def test_get_augmented_predictions_weighting(self, temp_storage_dir):
        """Test that RAG and rollup predictions are weighted correctly."""
        loop = FeedbackLoop()

        # Add rollup data
        for _ in range(5):
            loop.rollup.add_observation({
                "step_description": "Test the code",
                "actual_skills": ["test-skill"],
                "actual_tools": ["Bash"],
            })

        # Get predictions with RAG data
        result = loop.get_augmented_predictions(
            query="Test the code",
            rag_skills=["different-skill"],
            rag_tools=["Edit"],
            rag_weight=0.5,
            rollup_weight=0.5,
        )

        # Both should appear with combined scores
        skill_names = [s[0] for s in result["skills"]]
        assert "different-skill" in skill_names  # From RAG
        assert "test-skill" in skill_names  # From rollup

    def test_start_session(self, temp_storage_dir):
        """Test starting a session through feedback loop."""
        loop = FeedbackLoop()

        session = loop.start_session(
            step_description="Test step",
            predicted_skills=["skill-a"],
            predicted_tools=["Edit"],
        )

        assert session is not None
        assert get_active_session() is not None

        # Cleanup
        clear_active_session()

    def test_end_session_and_update(self, temp_storage_dir):
        """Test ending session and updating rollup."""
        loop = FeedbackLoop()

        # Start session
        loop.start_session(
            step_description="Test feature implementation",
            predicted_skills=["skill-a"],
            predicted_tools=["Edit"],
        )

        # Simulate some tool use
        record_tool_from_hook("Edit")
        record_tool_from_hook("Bash")

        # End session and update
        result = loop.end_session_and_update()

        assert result is not None
        assert result["rollup_updated"] is True
        assert result["rollup_total_observations"] == 1

        # Verify rollup was updated
        assert "test" in loop.rollup.keyword_observations or "feature" in loop.rollup.keyword_observations

    def test_end_session_no_active_session(self, temp_storage_dir):
        """Test ending session when none active."""
        loop = FeedbackLoop()
        clear_active_session()

        result = loop.end_session_and_update()
        assert result is None

    def test_get_feedback_stats(self, temp_storage_dir):
        """Test getting feedback loop statistics."""
        loop = FeedbackLoop()

        # Create some observations
        for i in range(3):
            usage = ActualUsage(
                session_id=f"stats{i}",
                step_description=f"Test step {i}",
                predicted_skills=["skill-a"],
                predicted_tools=["Edit"],
                actual_skills=["skill-a", "skill-b"],
                actual_tools=["Edit", "Bash"],
            )
            save_observation(usage)
            loop.rollup.add_observation({
                "step_description": f"Test step {i}",
                "actual_skills": ["skill-a", "skill-b"],
                "actual_tools": ["Edit", "Bash"],
            })

        stats = loop.get_feedback_stats()

        assert stats["total_observations"] == 3
        assert "skill_precision" in stats
        assert "skill_recall" in stats
        assert "suggestions" in stats
        assert stats["rollup_keywords"] > 0

    def test_reset_rollup(self, temp_storage_dir):
        """Test resetting the rollup."""
        loop = FeedbackLoop()

        # Add some data
        loop.rollup.add_observation({
            "step_description": "Test",
            "actual_skills": ["skill"],
            "actual_tools": ["Tool"],
        })
        assert loop.rollup.total_observations == 1

        # Reset
        loop.reset_rollup()

        assert loop.rollup.total_observations == 0

    def test_full_feedback_loop_cycle(self, temp_storage_dir):
        """Test a complete feedback loop cycle."""
        loop = FeedbackLoop()

        # Initial predictions (no rollup data yet)
        initial = loop.get_augmented_predictions(
            query="Plan the implementation",
            rag_skills=["starlog"],
            rag_tools=["Edit"],
        )

        # Start session with predictions
        predicted_skills = [s[0] for s in initial["skills"]]
        predicted_tools = [t[0] for t in initial["tools"]]

        loop.start_session(
            step_description="Plan the implementation",
            predicted_skills=predicted_skills,
            predicted_tools=predicted_tools,
        )

        # Simulate actual work
        record_tool_from_hook("Edit")
        record_tool_from_hook("Read")  # Used but not predicted

        # End session and update
        result = loop.end_session_and_update()

        assert result is not None
        assert "Read" in result["usage"]["tool_false_negatives"]

        # Now get new predictions - should incorporate learned pattern
        new_preds = loop.get_augmented_predictions(
            query="Plan the feature",  # Similar query
            rag_skills=["starlog"],
            rag_tools=["Edit"],
        )

        # Read should now appear because rollup learned "plan" → "Read"
        tool_names = [t[0] for t in new_preds["tools"]]
        assert "Read" in tool_names


class TestGetFeedbackLoop:
    """Tests for get_feedback_loop function."""

    def test_get_feedback_loop_creates_instance(self, temp_storage_dir):
        """Test that get_feedback_loop creates a singleton instance."""
        # Reset global
        import capability_predictor.tracking as tracking_module
        tracking_module._feedback_loop = None

        loop1 = get_feedback_loop()
        loop2 = get_feedback_loop()

        assert loop1 is loop2  # Same instance

        # Cleanup
        tracking_module._feedback_loop = None


class TestAugmentPredictionsWithFeedback:
    """Tests for augment_predictions_with_feedback convenience function."""

    def test_convenience_function(self, temp_storage_dir):
        """Test the convenience function."""
        # Reset global
        import capability_predictor.tracking as tracking_module
        tracking_module._feedback_loop = None

        result = augment_predictions_with_feedback(
            query="Test the feature",
            rag_skills=["test-skill"],
            rag_tools=["Bash"],
        )

        assert "skills" in result
        assert "tools" in result

        # Cleanup
        tracking_module._feedback_loop = None
