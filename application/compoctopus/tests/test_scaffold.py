"""Test that the entire Compoctopus package imports cleanly.

This is the Phase 0 sanity check: all stubs are importable,
all types are accessible, the algebra is structurally sound.
"""

import pytest


class TestImports:
    """Verify all modules import without errors."""

    def test_types_import(self):
        from compoctopus.types import (
            TaskSpec, FeatureType, TrustLevel, CompilationPhase,
            GeometricInvariant, ArmKind,
            MermaidSpec, PromptSection, ToolSpec, MCPConfig,
            ToolManifest, SkillSpec, SkillBundle,
            SystemPrompt, InputPrompt,
            ChainPlan, ChainNode, AgentProfile, CompiledAgent,
            AlignmentResult, GeometricAlignmentReport,
            SensorReading, GoldenChainEntry,
            RoutingNode, RoutingTree,
        )

    def test_errors_import(self):
        from compoctopus.errors import (
            CompoctopusError,
            CompilationError, ChainCompilationError,
            AgentCompilationError, MCPCompilationError,
            SkillCompilationError, SystemPromptCompilationError,
            InputPromptCompilationError,
            AlignmentError, DualDescriptionError,
            CapabilitySurfaceError, TrustBoundaryError,
            PhaseTemplateError, PolymorphicDispatchError,
            RegistryError, RoutingError, BridgeError,
        )

    def test_base_import(self):
        from compoctopus.base import CompilerArm, CompilerPipeline

    def test_context_import(self):
        from compoctopus.context import CompilationContext, CompilationStep

    def test_state_machine_import(self):
        from compoctopus.state_machine import (
            StateMachine, PhaseTransition, PhaseConfig,
            PhaseOutput, make_compiler_sm,
        )

    def test_alignment_import(self):
        from compoctopus.alignment import GeometricAlignmentValidator

    def test_mermaid_import(self):
        from compoctopus.mermaid import MermaidParser, MermaidGenerator, MermaidValidator

    def test_registry_import(self):
        from compoctopus.registry import (
            Registry, RegisteredMCP, RegisteredSkill, RegisteredDomain,
        )

    def test_arms_import(self):
        from compoctopus.arms import (
            ChainCompiler, AgentConfigCompiler, MCPCompiler,
            SkillCompiler, SystemPromptCompiler, InputPromptCompiler,
        )

    def test_router_import(self):
        from compoctopus.router import Bandit, ChainSelect, ChainConstruct

    def test_chain_ontology_import(self):
        from compoctopus.chain_ontology import Link, Chain, EvalChain, ConfigLink, LinkConfig

    def test_sensors_import(self):
        from compoctopus.sensors import SensorStore

    def test_golden_chains_import(self):
        from compoctopus.golden_chains import GoldenChainStore

    def test_onionmorph_import(self):
        from compoctopus.onionmorph import OnionmorphRouter

    def test_meta_import(self):
        from compoctopus.meta import MetaCompiler

    def test_package_import(self):
        """Test that the top-level package imports everything."""
        import compoctopus
        assert compoctopus.__version__ == "0.1.0"


class TestTypeAlgebra:
    """Verify the type algebra composes correctly."""

    def test_task_spec_creation(self):
        from compoctopus.types import TaskSpec, FeatureType, TrustLevel
        spec = TaskSpec(
            description="Summarize conversations",
            feature_type=FeatureType.AGENT,
            domain_hints=["summarization"],
            trust_level=TrustLevel.BUILDER,
        )
        assert spec.description == "Summarize conversations"
        assert spec.feature_type == FeatureType.AGENT

    def test_compilation_context_lifecycle(self):
        from compoctopus.types import TaskSpec, AgentProfile, ArmKind
        from compoctopus.context import CompilationContext
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        assert ctx.agent_profile is None
        ctx.agent_profile = AgentProfile(model="test-model")
        assert ctx.agent_profile.model == "test-model"
        agent = ctx.freeze()
        assert agent.agent_profile.model == "test-model"

    def test_geometric_alignment_report(self):
        from compoctopus.types import (
            AlignmentResult, GeometricInvariant, GeometricAlignmentReport,
        )
        report = GeometricAlignmentReport(results=[
            AlignmentResult(invariant=GeometricInvariant.DUAL_DESCRIPTION, passed=True),
            AlignmentResult(invariant=GeometricInvariant.CAPABILITY_SURFACE, passed=False,
                          violations=["Tool 'foo' in prompt but not equipped"]),
        ])
        assert not report.aligned
        assert len(report.violations) == 1

    def test_compiled_agent_completeness(self):
        from compoctopus.types import (
            TaskSpec, CompiledAgent, AgentProfile,
            ToolManifest, SystemPrompt, InputPrompt,
        )
        # Incomplete agent
        agent = CompiledAgent(task_spec=TaskSpec(description="test"))
        assert not agent.is_complete

        # Complete agent
        agent.agent_profile = AgentProfile()
        agent.tool_manifest = ToolManifest()
        agent.system_prompt = SystemPrompt()
        agent.input_prompt = InputPrompt()
        assert agent.is_complete

    def test_state_machine_transitions(self):
        from compoctopus.state_machine import make_compiler_sm
        from compoctopus.types import CompilationPhase
        sm = make_compiler_sm()
        assert sm.current_phase == CompilationPhase.ANALYZING
        assert not sm.is_terminal

        sm.transition("analyzed")
        assert sm.current_phase == CompilationPhase.COMPILING

        sm.transition("compiled")
        assert sm.current_phase == CompilationPhase.VALIDATING

        sm.transition("valid")
        assert sm.current_phase == CompilationPhase.COMPLETE
        assert sm.is_terminal

    def test_state_machine_debug_loop(self):
        from compoctopus.state_machine import make_compiler_sm
        from compoctopus.types import CompilationPhase
        sm = make_compiler_sm()
        sm.transition("analyzed")
        sm.transition("compiled")
        sm.transition("invalid")  # → DEBUG
        assert sm.current_phase == CompilationPhase.DEBUG

        sm.transition("fixed")  # → COMPILING
        assert sm.current_phase == CompilationPhase.COMPILING

    def test_arm_mermaid_specs_exist(self):
        """Every arm must have a non-empty mermaid spec."""
        from compoctopus.arms import (
            ChainCompiler, AgentConfigCompiler, MCPCompiler,
            SkillCompiler, SystemPromptCompiler, InputPromptCompiler,
        )
        for ArmClass in [ChainCompiler, AgentConfigCompiler, MCPCompiler,
                         SkillCompiler, SystemPromptCompiler, InputPromptCompiler]:
            arm = ArmClass()
            spec = arm.get_mermaid_spec()
            assert spec.diagram, f"{ArmClass.__name__} has empty mermaid diagram"
            assert spec.task_list, f"{ArmClass.__name__} has empty task list"

    def test_arm_system_prompt_sections_exist(self):
        """Every arm must have system prompt sections including IDENTITY."""
        from compoctopus.arms import (
            ChainCompiler, AgentConfigCompiler, MCPCompiler,
            SkillCompiler, SystemPromptCompiler, InputPromptCompiler,
        )
        for ArmClass in [ChainCompiler, AgentConfigCompiler, MCPCompiler,
                         SkillCompiler, SystemPromptCompiler, InputPromptCompiler]:
            arm = ArmClass()
            sections = arm.get_system_prompt_sections()
            assert sections, f"{ArmClass.__name__} has no sections"
            tags = [s.tag for s in sections]
            assert "IDENTITY" in tags, f"{ArmClass.__name__} missing IDENTITY"
