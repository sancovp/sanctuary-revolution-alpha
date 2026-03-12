"""
Tests for capability_predictor/core.py - Library Facade

Tests that the core module exports all expected functions and models.
"""

import pytest


class TestCoreImports:
    """Test that all expected items can be imported from core module."""

    def test_import_main_api(self):
        """Test importing main API functions."""
        from capability_predictor.core import (
            format_capability_prediction,
            predict_capabilities,
        )

        assert callable(predict_capabilities)
        assert callable(format_capability_prediction)

    def test_import_input_models(self):
        """Test importing input models."""
        from capability_predictor.core import CapabilityObservation, PlanStep

        # Verify they are Pydantic models
        assert hasattr(PlanStep, "model_fields")
        assert hasattr(CapabilityObservation, "model_fields")

    def test_import_output_models(self):
        """Test importing output models."""
        from capability_predictor.core import (
            CapabilityPrediction,
            PredictedServer,
            PredictedSkill,
            PredictedSkillDomain,
            PredictedSkillset,
            PredictedTool,
            PredictedToolDomain,
            StepPrediction,
        )

        # Verify they are Pydantic models
        models = [
            CapabilityPrediction,
            StepPrediction,
            PredictedSkill,
            PredictedSkillset,
            PredictedSkillDomain,
            PredictedTool,
            PredictedServer,
            PredictedToolDomain,
        ]
        for model in models:
            assert hasattr(model, "model_fields"), f"{model.__name__} is not a Pydantic model"

    def test_import_usage_tracking(self):
        """Test importing usage tracking model."""
        from capability_predictor.core import ActualUsage

        assert hasattr(ActualUsage, "model_fields")
        assert hasattr(ActualUsage, "skill_false_negatives")

    def test_import_low_level_rag(self):
        """Test importing low-level RAG functions."""
        from capability_predictor.core import (
            SkillRAGResult,
            ToolRAGResult,
            format_skill_rag_result,
            format_tool_rag_result,
            skill_rag_carton_style,
            tool_rag_carton_style,
        )

        assert callable(skill_rag_carton_style)
        assert callable(tool_rag_carton_style)
        assert callable(format_skill_rag_result)
        assert callable(format_tool_rag_result)


class TestPackageImports:
    """Test that the package-level imports work correctly."""

    def test_import_from_package(self):
        """Test importing directly from capability_predictor package."""
        from capability_predictor import (
            CapabilityObservation,
            CapabilityPrediction,
            PlanStep,
            StepPrediction,
            format_capability_prediction,
            predict_capabilities,
        )

        assert callable(predict_capabilities)
        assert callable(format_capability_prediction)
        assert hasattr(CapabilityObservation, "model_fields")
        assert hasattr(PlanStep, "model_fields")
        assert hasattr(CapabilityPrediction, "model_fields")
        assert hasattr(StepPrediction, "model_fields")


class TestAllExports:
    """Test the __all__ exports."""

    def test_core_all_exports(self):
        """Test that __all__ in core module lists expected items."""
        from capability_predictor import core

        expected_exports = [
            "predict_capabilities",
            "format_capability_prediction",
            "CapabilityObservation",
            "PlanStep",
            "CapabilityPrediction",
            "StepPrediction",
            "PredictedSkill",
            "PredictedSkillset",
            "PredictedSkillDomain",
            "PredictedTool",
            "PredictedServer",
            "PredictedToolDomain",
            "ActualUsage",
            "skill_rag_carton_style",
            "tool_rag_carton_style",
            "format_skill_rag_result",
            "format_tool_rag_result",
            "SkillRAGResult",
            "ToolRAGResult",
        ]

        for item in expected_exports:
            assert item in core.__all__, f"{item} not in core.__all__"

    def test_package_all_exports(self):
        """Test that __all__ in package lists expected items."""
        import capability_predictor

        expected_exports = [
            "predict_capabilities",
            "format_capability_prediction",
            "CapabilityObservation",
            "PlanStep",
            "CapabilityPrediction",
            "StepPrediction",
        ]

        for item in expected_exports:
            assert item in capability_predictor.__all__, f"{item} not in package __all__"


class TestModelConstruction:
    """Test that models can be constructed through core module imports."""

    def test_create_plan_step(self):
        """Test creating PlanStep through core import."""
        from capability_predictor.core import PlanStep

        step = PlanStep(step_number=1, description="Test step")
        assert step.step_number == 1
        assert step.description == "Test step"

    def test_create_capability_observation(self):
        """Test creating CapabilityObservation through core import."""
        from capability_predictor.core import CapabilityObservation, PlanStep

        obs = CapabilityObservation(
            steps=[
                PlanStep(step_number=1, description="Plan the task"),
                PlanStep(step_number=2, description="Execute the task"),
            ],
            context_domain="PAIAB",
        )

        assert len(obs.steps) == 2
        assert obs.context_domain == "PAIAB"

    def test_create_actual_usage(self):
        """Test creating ActualUsage for tracking."""
        from capability_predictor.core import ActualUsage

        usage = ActualUsage(
            session_id="test-session",
            step_description="Write some code",
            predicted_skills=["make-skill", "starlog"],
            predicted_tools=["Write", "Edit"],
            actual_skills=["starlog"],
            actual_tools=["Write", "Bash"],
        )

        assert usage.skill_true_positives == ["starlog"]
        assert usage.skill_false_positives == ["make-skill"]
        assert usage.tool_false_negatives == ["Bash"]
