"""
Tests for the Capability Predictor MCP Server.

Tests the MCP tool functions that wrap the library facade.
"""

import pytest
from unittest.mock import patch, MagicMock

from capability_predictor.mcp_server import (
    predict_capabilities_for_plan,
    format_prediction,
)
from capability_predictor.models import (
    CapabilityPrediction,
    StepPrediction,
    PredictedSkillDomain,
    PredictedToolDomain,
)


# === Test Data ===


def make_mock_prediction():
    """Create a mock CapabilityPrediction for testing."""
    return CapabilityPrediction(
        steps=[
            StepPrediction(
                step_number=1,
                description="Plan the project",
                skill_domains=[
                    PredictedSkillDomain(
                        name="navigation",
                        confidence=0.9,
                        skillsets=[],
                        orphan_skills=[]
                    )
                ],
                tool_domains=[
                    PredictedToolDomain(
                        name="general",
                        confidence=0.8,
                        servers=[],
                        orphan_tools=[]
                    )
                ],
                top_skills=["starlog", "waypoint"],
                top_tools=["bash", "read"]
            )
        ],
        overall_domains=["navigation", "general"],
        recommendations="Based on your plan, consider using navigation tools."
    )


# === Unit Tests: predict_capabilities_for_plan ===


class TestPredictCapabilitiesForPlan:
    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_converts_dict_steps_to_models(self, mock_predict):
        """Test that dict steps are properly converted to PlanStep models."""
        mock_predict.return_value = make_mock_prediction()

        steps = [
            {"step_number": 1, "description": "Plan the project"},
            {"step_number": 2, "description": "Implement logic"},
        ]

        result = predict_capabilities_for_plan(steps=steps)

        # Verify predict_capabilities was called
        mock_predict.assert_called_once()
        call_args = mock_predict.call_args[0][0]

        # Check observation was properly constructed
        assert len(call_args.steps) == 2
        assert call_args.steps[0].step_number == 1
        assert call_args.steps[0].description == "Plan the project"
        assert call_args.steps[1].step_number == 2

    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_passes_context_domain(self, mock_predict):
        """Test that context_domain is passed through."""
        mock_predict.return_value = make_mock_prediction()

        steps = [{"step_number": 1, "description": "Test"}]

        predict_capabilities_for_plan(steps=steps, context_domain="PAIAB")

        call_args = mock_predict.call_args[0][0]
        assert call_args.context_domain == "PAIAB"

    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_returns_dict(self, mock_predict):
        """Test that result is serialized to dict for MCP."""
        mock_predict.return_value = make_mock_prediction()

        steps = [{"step_number": 1, "description": "Test"}]

        result = predict_capabilities_for_plan(steps=steps)

        assert isinstance(result, dict)
        assert "steps" in result
        assert "overall_domains" in result
        assert "recommendations" in result

    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_result_structure(self, mock_predict):
        """Test the structure of the returned dict."""
        mock_predict.return_value = make_mock_prediction()

        steps = [{"step_number": 1, "description": "Plan the project"}]

        result = predict_capabilities_for_plan(steps=steps)

        # Check steps structure
        assert len(result["steps"]) == 1
        step = result["steps"][0]
        assert step["step_number"] == 1
        assert step["description"] == "Plan the project"
        assert "skill_domains" in step
        assert "tool_domains" in step
        assert step["top_skills"] == ["starlog", "waypoint"]
        assert step["top_tools"] == ["bash", "read"]

        # Check overall_domains
        assert result["overall_domains"] == ["navigation", "general"]

        # Check recommendations
        assert "navigation" in result["recommendations"]

    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_handles_none_context_domain(self, mock_predict):
        """Test that None context_domain works correctly."""
        mock_predict.return_value = make_mock_prediction()

        steps = [{"step_number": 1, "description": "Test"}]

        result = predict_capabilities_for_plan(steps=steps, context_domain=None)

        call_args = mock_predict.call_args[0][0]
        assert call_args.context_domain is None


# === Unit Tests: format_prediction ===


class TestFormatPrediction:
    def test_formats_prediction_dict(self):
        """Test that dict is properly formatted to string."""
        prediction = make_mock_prediction()
        prediction_dict = prediction.model_dump()

        result = format_prediction(prediction_dict)

        assert isinstance(result, str)
        assert "Capability Prediction" in result
        assert "Step 1" in result
        assert "starlog" in result
        assert "navigation" in result

    def test_handles_empty_prediction(self):
        """Test formatting empty prediction."""
        prediction = CapabilityPrediction(
            steps=[],
            overall_domains=[],
            recommendations=""
        )
        prediction_dict = prediction.model_dump()

        result = format_prediction(prediction_dict)

        assert isinstance(result, str)
        assert "Capability Prediction" in result

    def test_validates_dict_as_pydantic_model(self):
        """Test that invalid dict raises validation error."""
        invalid_dict = {"invalid": "data"}

        with pytest.raises(Exception):  # Pydantic ValidationError
            format_prediction(invalid_dict)


# === Integration Tests ===


class TestMcpServerIntegration:
    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_full_roundtrip(self, mock_predict):
        """Test predict → format roundtrip."""
        mock_predict.return_value = make_mock_prediction()

        # Predict
        steps = [
            {"step_number": 1, "description": "Plan the project"},
            {"step_number": 2, "description": "Write code"},
        ]
        prediction_dict = predict_capabilities_for_plan(steps=steps, context_domain="PAIAB")

        # Format
        formatted = format_prediction(prediction_dict)

        # Verify
        assert isinstance(formatted, str)
        assert "Step 1" in formatted
        assert "Plan the project" in formatted or "Plan the" in formatted

    @patch('capability_predictor.mcp_server.predict_capabilities')
    def test_complex_prediction_serialization(self, mock_predict):
        """Test that complex nested predictions serialize correctly."""
        from capability_predictor.models import (
            PredictedSkill,
            PredictedSkillset,
            PredictedTool,
            PredictedServer,
        )

        complex_prediction = CapabilityPrediction(
            steps=[
                StepPrediction(
                    step_number=1,
                    description="Complex step",
                    skill_domains=[
                        PredictedSkillDomain(
                            name="navigation",
                            confidence=0.9,
                            skillsets=[
                                PredictedSkillset(
                                    name="nav-skillset",
                                    domain="navigation",
                                    confidence=0.85,
                                    skills=[
                                        PredictedSkill(
                                            name="starlog",
                                            confidence=0.9,
                                            domain="navigation",
                                            category="preflight"
                                        )
                                    ]
                                )
                            ],
                            orphan_skills=[
                                PredictedSkill(
                                    name="orphan-skill",
                                    confidence=0.7,
                                    domain="navigation"
                                )
                            ]
                        )
                    ],
                    tool_domains=[
                        PredictedToolDomain(
                            name="code_analysis",
                            confidence=0.8,
                            servers=[
                                PredictedServer(
                                    name="context-alignment",
                                    domain="code_analysis",
                                    confidence=0.85,
                                    tools=[
                                        PredictedTool(
                                            name="get_context",
                                            confidence=0.9,
                                            server="context-alignment",
                                            domain="code_analysis"
                                        )
                                    ]
                                )
                            ],
                            orphan_tools=[]
                        )
                    ],
                    top_skills=["starlog", "orphan-skill"],
                    top_tools=["get_context"]
                )
            ],
            overall_domains=["navigation", "code_analysis"],
            recommendations="Use navigation and code analysis tools."
        )
        mock_predict.return_value = complex_prediction

        steps = [{"step_number": 1, "description": "Complex step"}]
        result = predict_capabilities_for_plan(steps=steps)

        # Verify nested structure is preserved
        assert len(result["steps"]) == 1
        step = result["steps"][0]

        # Check skill domains
        assert len(step["skill_domains"]) == 1
        skill_domain = step["skill_domains"][0]
        assert skill_domain["name"] == "navigation"
        assert len(skill_domain["skillsets"]) == 1
        assert skill_domain["skillsets"][0]["name"] == "nav-skillset"

        # Check tool domains
        assert len(step["tool_domains"]) == 1
        tool_domain = step["tool_domains"][0]
        assert tool_domain["name"] == "code_analysis"
        assert len(tool_domain["servers"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
