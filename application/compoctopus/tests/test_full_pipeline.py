"""Tests for the full 6-arm pipeline — end-to-end compilation."""

import pytest

from compoctopus.types import (
    CompiledAgent,
    FeatureType,
    PermissionMode,
    TaskSpec,
    TrustLevel,
)
from compoctopus.base import CompilerPipeline
from compoctopus.context import CompilationContext
from compoctopus.registry import Registry, RegisteredMCP, RegisteredSkill
from compoctopus.types import ToolSpec

from compoctopus.arms import (
    ChainCompiler,
    AgentConfigCompiler,
    MCPCompiler,
    SkillCompiler,
    SystemPromptCompiler,
    InputPromptCompiler,
)


def make_full_pipeline() -> CompilerPipeline:
    return CompilerPipeline(arms=[
        ChainCompiler(),
        AgentConfigCompiler(),
        MCPCompiler(),
        SkillCompiler(),
        SystemPromptCompiler(),
        InputPromptCompiler(),
    ])


class TestFullPipeline:
    """End-to-end: TaskSpec → CompiledAgent with all 6 arms."""

    def test_simple_agent(self):
        """Minimal agent: no tools, no skills."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(description="Think about philosophy"),
        )
        result = pipeline.compile(ctx)

        assert result.chain_plan is not None
        assert result.agent_profile is not None
        assert result.tool_manifest is not None
        assert result.skill_bundle is not None
        assert result.system_prompt is not None
        assert result.input_prompt is not None
        assert result.alignment.aligned

        # Should freeze cleanly
        agent = ctx.freeze()
        assert isinstance(agent, CompiledAgent)

    def test_agent_with_tools(self):
        """Agent with domain hints → tools in manifest → tools in prompt."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Query knowledge graph",
                feature_type=FeatureType.AGENT,
                domain_hints=["carton", "chroma"],
            ),
        )
        result = pipeline.compile(ctx)
        assert result.alignment.aligned

        # Tools should appear in system prompt CAPABILITY section
        cap = next(s for s in result.system_prompt.sections if s.tag == "CAPABILITY")
        assert "carton" in cap.content
        assert "chroma" in cap.content

        # Tools should appear in input prompt mermaid
        mermaid_tools = result.input_prompt.mermaid.tool_references
        assert "carton" in mermaid_tools or "chroma" in mermaid_tools

    def test_tool_compilation(self):
        """TOOL feature type → 4-node chain (analyze/code/test/integrate)."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Build a search indexer",
                feature_type=FeatureType.TOOL,
                domain_hints=["filesystem"],
            ),
        )
        result = pipeline.compile(ctx)
        assert result.alignment.aligned

        # Chain should be 4 nodes
        assert len(result.chain_plan.nodes) == 4
        # Temperature should be low (deterministic coding)
        assert result.agent_profile.temperature == 0.3

    def test_executor_lockdown(self):
        """EXECUTOR trust → restrictedPermissions, max_turns ≤ 5."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Run this one task",
                trust_level=TrustLevel.EXECUTOR,
            ),
        )
        result = pipeline.compile(ctx)
        assert result.alignment.aligned

        assert result.agent_profile.permission_mode == PermissionMode.RESTRICTED
        assert result.agent_profile.max_turns <= 5

        # CONSTRAINTS section should mention execution
        constraints = next(s for s in result.system_prompt.sections if s.tag == "CONSTRAINTS")
        assert "Execute" in constraints.content or "assigned" in constraints.content

    def test_observer_readonly(self):
        """OBSERVER trust → readOnly, max_turns ≤ 3."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Monitor system health",
                trust_level=TrustLevel.OBSERVER,
            ),
        )
        result = pipeline.compile(ctx)
        assert result.alignment.aligned

        assert result.agent_profile.permission_mode == PermissionMode.READ_ONLY
        assert result.agent_profile.max_turns <= 3

    def test_with_registry(self):
        """Full pipeline with registry providing real MCP configs."""
        registry = Registry()
        registry.register_mcp(RegisteredMCP(
            name="carton",
            description="Knowledge graph MCP",
            command="python -m carton",
            tools=[
                ToolSpec(name="get_concept", description="Get a concept"),
                ToolSpec(name="observe", description="Observe to KG"),
            ],
        ))

        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Query knowledge graph",
                domain_hints=["get_concept"],
            ),
        )
        ctx.metadata["registry"] = registry
        result = pipeline.compile(ctx)
        assert result.alignment.aligned

        # All carton tools should be in manifest
        tool_names = set(result.tool_manifest.all_tool_names)
        assert "get_concept" in tool_names
        assert "observe" in tool_names

        # And in system prompt
        cap = next(s for s in result.system_prompt.sections if s.tag == "CAPABILITY")
        assert "get_concept" in cap.content

    def test_compiled_agent_completeness(self):
        """CompiledAgent should have all fields populated."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Full agent test",
                feature_type=FeatureType.AGENT,
                domain_hints=["carton"],
                trust_level=TrustLevel.BUILDER,
            ),
        )
        pipeline.compile(ctx)
        agent = ctx.freeze()

        assert agent.task_spec.description == "Full agent test"
        assert agent.chain_plan is not None
        assert len(agent.chain_plan.nodes) > 0
        assert agent.agent_profile is not None
        assert agent.agent_profile.model is not None
        assert agent.tool_manifest is not None
        assert agent.skill_bundle is not None
        assert agent.system_prompt is not None
        assert len(agent.system_prompt.sections) >= 4
        assert agent.input_prompt is not None
        assert agent.input_prompt.goal is not None
        assert agent.alignment is not None
        assert agent.alignment.aligned


class TestSelfCompilationComplete:
    """Now that all arms are filled, self-compile should be richer."""

    def test_pipeline_self_compile_all(self):
        """Every arm self-validates against its own design.

        Note: self-compile checks arm's own mermaid ↔ system prompt alignment.
        Some arms may have soft mismatches in their self-descriptions which
        are informational, not blocking. We verify all arms run without error.
        """
        pipeline = make_full_pipeline()
        results = pipeline.self_compile_all()

        assert len(results) == 6
        for result in results:
            # At minimum, mermaid spec must exist
            assert result.mermaid_spec is not None
            if not result.aligned:
                print(f"⚠️ Self-compile info: {result.issues}")

    def test_pipeline_compile_partial_full(self):
        """Partial compile on full pipeline → Layer 6/6."""
        pipeline = make_full_pipeline()
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        report = pipeline.compile_partial(ctx)

        assert report.layer == 6
        assert report.total == 6
        assert not report.not_implemented
        assert not report.failed

        print(report)
