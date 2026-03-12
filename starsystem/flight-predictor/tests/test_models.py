"""Tests for Pydantic models in capability_predictor/models.py."""

import pytest
from pydantic import ValidationError

from capability_predictor.models import (
    ActualUsage,
    CapabilityObservation,
    CapabilityPrediction,
    PlanStep,
    PredictedServer,
    PredictedSkill,
    PredictedSkillDomain,
    PredictedSkillset,
    PredictedTool,
    PredictedToolDomain,
    StepPrediction,
)


# ============================================================================
# PlanStep Tests
# ============================================================================


class TestPlanStep:
    def test_valid_plan_step(self):
        """Test creating a valid PlanStep."""
        step = PlanStep(step_number=1, description="Plan the project")
        assert step.step_number == 1
        assert step.description == "Plan the project"

    def test_step_number_must_be_positive(self):
        """Test that step_number must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            PlanStep(step_number=0, description="Invalid step")
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_description_cannot_be_empty(self):
        """Test that description cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PlanStep(step_number=1, description="")
        # Pydantic uses different error messages across versions
        error_str = str(exc_info.value).lower()
        assert "string_too_short" in error_str or "at least 1 character" in error_str


# ============================================================================
# CapabilityObservation Tests
# ============================================================================


class TestCapabilityObservation:
    def test_valid_observation(self):
        """Test creating a valid CapabilityObservation."""
        obs = CapabilityObservation(
            steps=[
                PlanStep(step_number=1, description="Step one"),
                PlanStep(step_number=2, description="Step two"),
            ],
            context_domain="PAIAB",
        )
        assert len(obs.steps) == 2
        assert obs.context_domain == "PAIAB"

    def test_observation_requires_at_least_one_step(self):
        """Test that observation needs at least one step."""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityObservation(steps=[])
        # Pydantic uses different error messages across versions
        error_str = str(exc_info.value).lower()
        assert "too_short" in error_str or "at least 1 item" in error_str

    def test_context_domain_is_optional(self):
        """Test that context_domain is optional."""
        obs = CapabilityObservation(
            steps=[PlanStep(step_number=1, description="Step one")]
        )
        assert obs.context_domain is None


# ============================================================================
# Predicted Skill Models Tests
# ============================================================================


class TestPredictedSkill:
    def test_valid_predicted_skill(self):
        """Test creating a valid PredictedSkill."""
        skill = PredictedSkill(
            name="starlog",
            confidence=0.85,
            skillset="navigation-skillset",
            domain="navigation",
            category="preflight",
        )
        assert skill.name == "starlog"
        assert skill.confidence == 0.85
        assert skill.skillset == "navigation-skillset"
        assert skill.domain == "navigation"
        assert skill.category == "preflight"

    def test_confidence_must_be_in_range(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            PredictedSkill(name="test", confidence=1.5, domain="test")
        with pytest.raises(ValidationError):
            PredictedSkill(name="test", confidence=-0.1, domain="test")


class TestPredictedSkillset:
    def test_valid_skillset(self):
        """Test creating a valid PredictedSkillset."""
        skillset = PredictedSkillset(
            name="navigation-skillset",
            domain="navigation",
            confidence=0.9,
            skills=[
                PredictedSkill(name="starlog", confidence=0.95, domain="navigation"),
                PredictedSkill(name="waypoint", confidence=0.85, domain="navigation"),
            ],
        )
        assert len(skillset.skills) == 2
        assert skillset.confidence == 0.9


class TestPredictedSkillDomain:
    def test_valid_domain(self):
        """Test creating a valid PredictedSkillDomain."""
        domain = PredictedSkillDomain(
            name="navigation",
            confidence=0.88,
            skillsets=[
                PredictedSkillset(
                    name="nav-set",
                    domain="navigation",
                    confidence=0.9,
                    skills=[],
                )
            ],
            orphan_skills=[
                PredictedSkill(name="orphan", confidence=0.7, domain="navigation")
            ],
        )
        assert domain.name == "navigation"
        assert len(domain.skillsets) == 1
        assert len(domain.orphan_skills) == 1


# ============================================================================
# Predicted Tool Models Tests
# ============================================================================


class TestPredictedTool:
    def test_valid_predicted_tool(self):
        """Test creating a valid PredictedTool."""
        tool = PredictedTool(
            name="get_dependency_context",
            confidence=0.92,
            server="context-alignment",
            domain="code_analysis",
            description="Get dependency graph for code",
        )
        assert tool.name == "get_dependency_context"
        assert tool.server == "context-alignment"


class TestPredictedServer:
    def test_valid_server(self):
        """Test creating a valid PredictedServer."""
        server = PredictedServer(
            name="context-alignment",
            domain="code_analysis",
            confidence=0.88,
            tools=[
                PredictedTool(
                    name="parse_repo",
                    confidence=0.9,
                    server="context-alignment",
                    domain="code_analysis",
                )
            ],
        )
        assert len(server.tools) == 1


class TestPredictedToolDomain:
    def test_valid_tool_domain(self):
        """Test creating a valid PredictedToolDomain."""
        domain = PredictedToolDomain(
            name="code_analysis",
            confidence=0.85,
            servers=[],
            orphan_tools=[],
        )
        assert domain.name == "code_analysis"


# ============================================================================
# StepPrediction Tests
# ============================================================================


class TestStepPrediction:
    def test_valid_step_prediction(self):
        """Test creating a valid StepPrediction."""
        pred = StepPrediction(
            step_number=1,
            description="Plan the project",
            skill_domains=[
                PredictedSkillDomain(
                    name="navigation", confidence=0.9, skillsets=[], orphan_skills=[]
                )
            ],
            tool_domains=[
                PredictedToolDomain(
                    name="planning", confidence=0.8, servers=[], orphan_tools=[]
                )
            ],
            top_skills=["starlog", "waypoint"],
            top_tools=["plot_course", "fly"],
        )
        assert pred.step_number == 1
        assert len(pred.top_skills) == 2
        assert len(pred.top_tools) == 2


# ============================================================================
# CapabilityPrediction Tests
# ============================================================================


class TestCapabilityPrediction:
    def test_valid_prediction(self):
        """Test creating a valid CapabilityPrediction."""
        pred = CapabilityPrediction(
            steps=[
                StepPrediction(
                    step_number=1,
                    description="Step one",
                    skill_domains=[],
                    tool_domains=[],
                    top_skills=["skill1"],
                    top_tools=["tool1"],
                ),
            ],
            overall_domains=["navigation", "building"],
            recommendations="Consider using starlog for tracking.",
        )
        assert len(pred.steps) == 1
        assert len(pred.overall_domains) == 2


# ============================================================================
# ActualUsage Tests
# ============================================================================


class TestActualUsage:
    def test_valid_usage(self):
        """Test creating valid ActualUsage."""
        usage = ActualUsage(
            session_id="test-123",
            step_description="Plan the project",
            predicted_skills=["starlog", "waypoint"],
            predicted_tools=["plot_course"],
            actual_skills=["starlog", "flight-config"],
            actual_tools=["plot_course", "fly"],
        )
        assert usage.session_id == "test-123"

    def test_skill_false_negatives(self):
        """Test skill false negatives (used but not predicted)."""
        usage = ActualUsage(
            session_id="test",
            step_description="test",
            predicted_skills=["a", "b"],
            actual_skills=["b", "c", "d"],
        )
        assert set(usage.skill_false_negatives) == {"c", "d"}

    def test_skill_false_positives(self):
        """Test skill false positives (predicted but not used)."""
        usage = ActualUsage(
            session_id="test",
            step_description="test",
            predicted_skills=["a", "b", "c"],
            actual_skills=["b"],
        )
        assert set(usage.skill_false_positives) == {"a", "c"}

    def test_skill_true_positives(self):
        """Test skill true positives (predicted and used)."""
        usage = ActualUsage(
            session_id="test",
            step_description="test",
            predicted_skills=["a", "b", "c"],
            actual_skills=["b", "c", "d"],
        )
        assert set(usage.skill_true_positives) == {"b", "c"}

    def test_tool_false_negatives(self):
        """Test tool false negatives."""
        usage = ActualUsage(
            session_id="test",
            step_description="test",
            predicted_tools=["tool1"],
            actual_tools=["tool1", "tool2"],
        )
        assert usage.tool_false_negatives == ["tool2"]

    def test_tool_false_positives(self):
        """Test tool false positives."""
        usage = ActualUsage(
            session_id="test",
            step_description="test",
            predicted_tools=["tool1", "tool2"],
            actual_tools=["tool1"],
        )
        assert usage.tool_false_positives == ["tool2"]

    def test_tool_true_positives(self):
        """Test tool true positives."""
        usage = ActualUsage(
            session_id="test",
            step_description="test",
            predicted_tools=["tool1", "tool2"],
            actual_tools=["tool1", "tool3"],
        )
        assert usage.tool_true_positives == ["tool1"]
