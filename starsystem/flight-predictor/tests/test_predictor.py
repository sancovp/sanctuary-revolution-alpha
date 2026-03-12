"""
Tests for the Capability Predictor.

Tests the main predict_capabilities() function that joins skill and tool RAG
to provide unified capability predictions for plan steps.
"""

import pytest
from unittest.mock import patch, MagicMock

from capability_predictor.models import (
    CapabilityObservation,
    CapabilityPrediction,
    PlanStep,
    PredictedSkill,
    PredictedSkillDomain,
    PredictedSkillset,
    PredictedServer,
    PredictedTool,
    PredictedToolDomain,
    StepPrediction,
)
from capability_predictor.predictor import (
    _convert_skill_result,
    _convert_tool_result,
    _extract_top_skills,
    _extract_top_tools,
    _aggregate_overall_domains,
    _generate_recommendations,
    predict_capabilities,
    format_capability_prediction,
)
from capability_predictor.skill_rag import (
    SkillHit,
    SkillsetAggregation,
    DomainAggregation,
    SkillRAGResult,
)
from capability_predictor.tool_rag import (
    ToolHit,
    ServerAggregation,
    ToolDomainAggregation,
    ToolRAGResult,
)


# === Test Data Helpers ===


def make_skill_hit(name: str, domain: str = "general", score: float = 0.8,
                   subdomain: str = "", category: str = "", skillset: str = None) -> SkillHit:
    """Helper to create test SkillHit."""
    return SkillHit(
        name=name,
        domain=domain,
        subdomain=subdomain,
        category=category,
        score=score,
        skillset=skillset
    )


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


def make_skill_rag_result(query: str = "test",
                          domains: list[DomainAggregation] = None,
                          raw_hits: list[SkillHit] = None) -> SkillRAGResult:
    """Helper to create test SkillRAGResult."""
    return SkillRAGResult(
        query=query,
        domains=domains or [],
        raw_hits=raw_hits or []
    )


def make_tool_rag_result(query: str = "test",
                         domains: list[ToolDomainAggregation] = None,
                         raw_hits: list[ToolHit] = None) -> ToolRAGResult:
    """Helper to create test ToolRAGResult."""
    return ToolRAGResult(
        query=query,
        domains=domains or [],
        raw_hits=raw_hits or []
    )


# === Unit Tests: Conversion Functions ===


class TestConvertSkillResult:
    def test_empty_result(self):
        result = make_skill_rag_result()
        converted = _convert_skill_result(result)
        assert converted == []

    def test_converts_domain_with_orphan_skills(self):
        hit = make_skill_hit("starlog", "navigation", 0.9, category="preflight")
        domain = DomainAggregation(
            name="navigation",
            skillsets=[],
            orphan_skills=[hit],
            confidence=0.9
        )
        result = make_skill_rag_result(domains=[domain], raw_hits=[hit])

        converted = _convert_skill_result(result)

        assert len(converted) == 1
        assert isinstance(converted[0], PredictedSkillDomain)
        assert converted[0].name == "navigation"
        assert converted[0].confidence == 0.9
        assert len(converted[0].orphan_skills) == 1
        assert converted[0].orphan_skills[0].name == "starlog"
        assert converted[0].orphan_skills[0].category == "preflight"

    def test_converts_domain_with_skillsets(self):
        hit = make_skill_hit("starlog", "navigation", 0.9, skillset="nav-set")
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
        result = make_skill_rag_result(domains=[domain], raw_hits=[hit])

        converted = _convert_skill_result(result)

        assert len(converted) == 1
        assert len(converted[0].skillsets) == 1
        assert converted[0].skillsets[0].name == "nav-set"
        assert len(converted[0].skillsets[0].skills) == 1


class TestConvertToolResult:
    def test_empty_result(self):
        result = make_tool_rag_result()
        converted = _convert_tool_result(result)
        assert converted == []

    def test_converts_domain_with_servers(self):
        hit = make_tool_hit("get_context", "context-alignment", "code_analysis", 0.85)
        server = ServerAggregation(
            name="context-alignment",
            domain="code_analysis",
            tools=[hit],
            confidence=0.85
        )
        domain = ToolDomainAggregation(
            name="code_analysis",
            servers=[server],
            orphan_tools=[],
            confidence=0.85
        )
        result = make_tool_rag_result(domains=[domain], raw_hits=[hit])

        converted = _convert_tool_result(result)

        assert len(converted) == 1
        assert isinstance(converted[0], PredictedToolDomain)
        assert converted[0].name == "code_analysis"
        assert len(converted[0].servers) == 1
        assert converted[0].servers[0].name == "context-alignment"

    def test_converts_orphan_tools(self):
        hit = make_tool_hit("lone_tool", "unknown", "general", 0.7)
        domain = ToolDomainAggregation(
            name="general",
            servers=[],
            orphan_tools=[hit],
            confidence=0.7
        )
        result = make_tool_rag_result(domains=[domain], raw_hits=[hit])

        converted = _convert_tool_result(result)

        assert len(converted) == 1
        assert len(converted[0].orphan_tools) == 1
        assert converted[0].orphan_tools[0].name == "lone_tool"


# === Unit Tests: Extraction Functions ===


class TestExtractTopSkills:
    def test_empty_domains(self):
        result = _extract_top_skills([])
        assert result == []

    def test_extracts_from_skillsets(self):
        domains = [
            PredictedSkillDomain(
                name="navigation",
                confidence=0.9,
                skillsets=[
                    PredictedSkillset(
                        name="nav-set",
                        domain="navigation",
                        confidence=0.85,
                        skills=[
                            PredictedSkill(name="starlog", confidence=0.9, domain="navigation"),
                            PredictedSkill(name="waypoint", confidence=0.8, domain="navigation"),
                        ]
                    )
                ],
                orphan_skills=[]
            )
        ]

        result = _extract_top_skills(domains, limit=2)

        assert len(result) == 2
        assert result[0] == "starlog"  # Higher confidence first
        assert result[1] == "waypoint"

    def test_extracts_from_orphans(self):
        domains = [
            PredictedSkillDomain(
                name="general",
                confidence=0.7,
                skillsets=[],
                orphan_skills=[
                    PredictedSkill(name="orphan-a", confidence=0.7, domain="general"),
                    PredictedSkill(name="orphan-b", confidence=0.6, domain="general"),
                ]
            )
        ]

        result = _extract_top_skills(domains, limit=5)

        assert len(result) == 2
        assert result[0] == "orphan-a"
        assert result[1] == "orphan-b"


class TestExtractTopTools:
    def test_empty_domains(self):
        result = _extract_top_tools([])
        assert result == []

    def test_respects_limit(self):
        domains = [
            PredictedToolDomain(
                name="general",
                confidence=0.8,
                servers=[],
                orphan_tools=[
                    PredictedTool(name=f"tool-{i}", confidence=0.9 - i * 0.1, server="s", domain="general")
                    for i in range(10)
                ]
            )
        ]

        result = _extract_top_tools(domains, limit=3)

        assert len(result) == 3
        assert result[0] == "tool-0"  # Highest confidence


# === Unit Tests: Aggregation ===


class TestAggregateOverallDomains:
    def test_empty_steps(self):
        result = _aggregate_overall_domains([])
        assert result == []

    def test_aggregates_across_steps(self):
        steps = [
            StepPrediction(
                step_number=1,
                description="Step 1",
                skill_domains=[
                    PredictedSkillDomain(name="navigation", confidence=0.9, skillsets=[], orphan_skills=[])
                ],
                tool_domains=[
                    PredictedToolDomain(name="code_analysis", confidence=0.8, servers=[], orphan_tools=[])
                ],
                top_skills=[],
                top_tools=[]
            ),
            StepPrediction(
                step_number=2,
                description="Step 2",
                skill_domains=[
                    PredictedSkillDomain(name="navigation", confidence=0.85, skillsets=[], orphan_skills=[])
                ],
                tool_domains=[],
                top_skills=[],
                top_tools=[]
            )
        ]

        result = _aggregate_overall_domains(steps)

        assert "navigation" in result
        # navigation should be first (highest combined score: 0.9 + 0.85 = 1.75)
        assert result[0] == "navigation"


# === Unit Tests: Recommendations ===


class TestGenerateRecommendations:
    def test_empty_steps(self):
        result = _generate_recommendations([], [], None)
        assert result == "No predictions available."

    def test_includes_overall_domains(self):
        steps = [
            StepPrediction(
                step_number=1, description="test",
                skill_domains=[], tool_domains=[],
                top_skills=["starlog"], top_tools=["bash"]
            )
        ]
        result = _generate_recommendations(steps, ["navigation", "building"], None)

        assert "navigation" in result
        assert "building" in result

    def test_context_domain_alignment(self):
        steps = [
            StepPrediction(
                step_number=1, description="test",
                skill_domains=[], tool_domains=[],
                top_skills=[], top_tools=[]
            )
        ]

        # Matching context
        result = _generate_recommendations(steps, ["navigation"], "NAVIGATION")
        assert "aligns well" in result

        # Non-matching context
        result = _generate_recommendations(steps, ["navigation"], "CAVE")
        assert "differs from" in result


# === Integration Tests ===


class TestPredictCapabilities:
    @patch('capability_predictor.predictor.tool_rag_carton_style')
    @patch('capability_predictor.predictor.skill_rag_carton_style')
    def test_basic_prediction(self, mock_skill_rag, mock_tool_rag):
        """Test basic prediction pipeline with mocked RAG functions."""
        # Mock skill RAG
        skill_hit = make_skill_hit("starlog", "navigation", 0.9)
        mock_skill_rag.return_value = make_skill_rag_result(
            domains=[DomainAggregation(
                name="navigation",
                skillsets=[],
                orphan_skills=[skill_hit],
                confidence=0.9
            )],
            raw_hits=[skill_hit]
        )

        # Mock tool RAG
        tool_hit = make_tool_hit("bash", "bash-server", "general", 0.8)
        mock_tool_rag.return_value = make_tool_rag_result(
            domains=[ToolDomainAggregation(
                name="general",
                servers=[],
                orphan_tools=[tool_hit],
                confidence=0.8
            )],
            raw_hits=[tool_hit]
        )

        observation = CapabilityObservation(
            steps=[PlanStep(step_number=1, description="Plan the project")],
            context_domain="PAIAB"
        )

        result = predict_capabilities(observation)

        assert isinstance(result, CapabilityPrediction)
        assert len(result.steps) == 1
        assert result.steps[0].step_number == 1
        assert "starlog" in result.steps[0].top_skills
        assert "bash" in result.steps[0].top_tools

    @patch('capability_predictor.predictor.tool_rag_carton_style')
    @patch('capability_predictor.predictor.skill_rag_carton_style')
    def test_multiple_steps(self, mock_skill_rag, mock_tool_rag):
        """Test prediction with multiple steps."""
        mock_skill_rag.return_value = make_skill_rag_result()
        mock_tool_rag.return_value = make_tool_rag_result()

        observation = CapabilityObservation(
            steps=[
                PlanStep(step_number=1, description="Step one"),
                PlanStep(step_number=2, description="Step two"),
                PlanStep(step_number=3, description="Step three"),
            ]
        )

        result = predict_capabilities(observation)

        assert len(result.steps) == 3
        assert result.steps[0].step_number == 1
        assert result.steps[1].step_number == 2
        assert result.steps[2].step_number == 3

    @patch('capability_predictor.predictor.tool_rag_carton_style')
    @patch('capability_predictor.predictor.skill_rag_carton_style')
    def test_empty_rag_results(self, mock_skill_rag, mock_tool_rag):
        """Test handling when RAG returns no results."""
        mock_skill_rag.return_value = make_skill_rag_result()
        mock_tool_rag.return_value = make_tool_rag_result()

        observation = CapabilityObservation(
            steps=[PlanStep(step_number=1, description="Unknown task")]
        )

        result = predict_capabilities(observation)

        assert len(result.steps) == 1
        assert result.steps[0].top_skills == []
        assert result.steps[0].top_tools == []


# === Formatting Tests ===


class TestFormatCapabilityPrediction:
    def test_format_empty_prediction(self):
        prediction = CapabilityPrediction(
            steps=[],
            overall_domains=[],
            recommendations=""
        )

        output = format_capability_prediction(prediction)

        assert "Capability Prediction" in output

    def test_format_full_prediction(self):
        prediction = CapabilityPrediction(
            steps=[
                StepPrediction(
                    step_number=1,
                    description="Plan the project structure",
                    skill_domains=[
                        PredictedSkillDomain(name="navigation", confidence=0.9, skillsets=[], orphan_skills=[])
                    ],
                    tool_domains=[
                        PredictedToolDomain(name="general", confidence=0.8, servers=[], orphan_tools=[])
                    ],
                    top_skills=["starlog", "waypoint"],
                    top_tools=["bash", "read"]
                )
            ],
            overall_domains=["navigation", "general"],
            recommendations="Based on your plan..."
        )

        output = format_capability_prediction(prediction)

        assert "Step 1" in output
        assert "starlog" in output
        assert "waypoint" in output
        assert "navigation" in output


# === Model Tests ===


class TestPlanStep:
    def test_valid_step(self):
        step = PlanStep(step_number=1, description="Do something")
        assert step.step_number == 1
        assert step.description == "Do something"

    def test_step_number_must_be_positive(self):
        with pytest.raises(ValueError):
            PlanStep(step_number=0, description="Invalid")

    def test_description_cannot_be_empty(self):
        with pytest.raises(ValueError):
            PlanStep(step_number=1, description="")


class TestCapabilityObservation:
    def test_valid_observation(self):
        obs = CapabilityObservation(
            steps=[PlanStep(step_number=1, description="Test")],
            context_domain="PAIAB"
        )
        assert len(obs.steps) == 1
        assert obs.context_domain == "PAIAB"

    def test_steps_cannot_be_empty(self):
        with pytest.raises(ValueError):
            CapabilityObservation(steps=[])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
