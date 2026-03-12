"""Tests for Phase 2: Filled arms (Chain, Agent, MCP)."""

import pytest

from compoctopus.types import (
    AgentProfile,
    ArmKind,
    ChainNode,
    ChainPlan,
    FeatureType,
    MCPConfig,
    PermissionMode,
    TaskSpec,
    ToolManifest,
    ToolSpec,
    TrustLevel,
)
from compoctopus.base import CompilerPipeline
from compoctopus.context import CompilationContext
from compoctopus.registry import Registry, RegisteredMCP

from compoctopus.arms import (
    ChainCompiler,
    AgentConfigCompiler,
    MCPCompiler,
)


class TestChainCompiler:
    """Test chain decomposition by feature type."""

    def test_tool_decomposition(self):
        """TOOL → analyze→code→test→integrate."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Build a search tool",
                feature_type=FeatureType.TOOL,
            ),
        )
        arm = ChainCompiler()
        arm.compile(ctx)

        assert ctx.chain_plan is not None
        names = [n.name for n in ctx.chain_plan.nodes]
        assert names == ["analyze", "code", "test", "integrate"]
        assert ctx.chain_plan.flow_type == "sequential"
        assert "code" in ctx.chain_plan.dependencies
        assert ctx.chain_plan.dependencies["code"] == ["analyze"]

    def test_agent_decomposition(self):
        """AGENT → design→config→validate."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Build a summarizer agent",
                feature_type=FeatureType.AGENT,
            ),
        )
        arm = ChainCompiler()
        arm.compile(ctx)

        names = [n.name for n in ctx.chain_plan.nodes]
        assert names == ["design", "config", "validate"]

    def test_domain_decomposition(self):
        """DOMAIN → domain→subdomain→workers."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Knowledge management domain",
                feature_type=FeatureType.DOMAIN,
                domain_hints=["carton", "chroma"],
            ),
        )
        arm = ChainCompiler()
        arm.compile(ctx)

        names = [n.name for n in ctx.chain_plan.nodes]
        assert names == ["domain", "subdomain", "workers"]
        # Domain hints should propagate to first node
        assert "carton" in ctx.chain_plan.nodes[0].requires_mcps

    def test_chain_validates_dag(self):
        """Validation should pass for valid DAG, fail for issues."""
        arm = ChainCompiler()

        # Valid
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        arm.compile(ctx)
        report = arm.validate(ctx)
        assert report.aligned, f"Violations: {report.violations}"

    def test_chain_validates_empty_plan(self):
        """Empty chain plan → validation failure."""
        arm = ChainCompiler()
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        ctx.chain_plan = ChainPlan()
        report = arm.validate(ctx)
        assert not report.aligned

    def test_chain_validates_duplicate_names(self):
        """Duplicate node names → validation failure."""
        arm = ChainCompiler()
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        ctx.chain_plan = ChainPlan(nodes=[
            ChainNode(name="step1"),
            ChainNode(name="step1"),  # Duplicate!
        ])
        report = arm.validate(ctx)
        assert not report.aligned
        assert any("Duplicate" in v for v in report.violations)


class TestAgentConfigCompiler:
    """Test agent profile generation."""

    def test_executor_trust(self):
        """EXECUTOR → restricted permissions, max_turns ≤ 5."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Simple task",
                trust_level=TrustLevel.EXECUTOR,
            ),
        )
        ChainCompiler().compile(ctx)
        AgentConfigCompiler().compile(ctx)

        assert ctx.agent_profile is not None
        assert ctx.agent_profile.permission_mode == PermissionMode.RESTRICTED
        assert ctx.agent_profile.max_turns <= 5

    def test_observer_trust(self):
        """OBSERVER → read-only, max_turns ≤ 3."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Monitor",
                trust_level=TrustLevel.OBSERVER,
            ),
        )
        ChainCompiler().compile(ctx)
        AgentConfigCompiler().compile(ctx)

        assert ctx.agent_profile.permission_mode == PermissionMode.READ_ONLY
        assert ctx.agent_profile.max_turns <= 3

    def test_tool_temperature(self):
        """TOOL feature → low temperature (0.3) for deterministic coding."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Build tool",
                feature_type=FeatureType.TOOL,
            ),
        )
        ChainCompiler().compile(ctx)
        AgentConfigCompiler().compile(ctx)

        assert ctx.agent_profile.temperature == 0.3

    def test_orchestrator_gets_claude(self):
        """ORCHESTRATOR trust → bigger model."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Route tasks",
                trust_level=TrustLevel.ORCHESTRATOR,
            ),
        )
        ChainCompiler().compile(ctx)
        AgentConfigCompiler().compile(ctx)

        assert "claude" in ctx.agent_profile.model

    def test_validation_passes(self):
        """Valid profile should pass trust boundary check."""
        ctx = CompilationContext(
            task_spec=TaskSpec(description="test"),
        )
        ChainCompiler().compile(ctx)
        arm = AgentConfigCompiler()
        arm.compile(ctx)
        report = arm.validate(ctx)
        assert report.aligned


class TestMCPCompiler:
    """Test MCP resolution."""

    def test_no_hints_empty_manifest(self):
        """No domain hints or MCP requirements → empty manifest."""
        ctx = CompilationContext(
            task_spec=TaskSpec(description="Think about things"),
        )
        ChainCompiler().compile(ctx)
        MCPCompiler().compile(ctx)

        assert ctx.tool_manifest is not None
        assert len(ctx.tool_manifest.all_tool_names) == 0

    def test_domain_hints_create_tools(self):
        """Domain hints → tools in manifest."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Query knowledge",
                domain_hints=["carton", "chroma"],
            ),
        )
        ChainCompiler().compile(ctx)
        MCPCompiler().compile(ctx)

        names = set(ctx.tool_manifest.all_tool_names)
        assert "carton" in names
        assert "chroma" in names

    def test_registry_integration(self):
        """With a registry, should resolve real MCP configs."""
        registry = Registry()
        registry.register_mcp(RegisteredMCP(
            name="carton",
            description="Knowledge graph",
            command="python -m carton",
            tools=[
                ToolSpec(name="get_concept"),
                ToolSpec(name="observe"),
            ],
        ))

        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Query KG",
                domain_hints=["get_concept"],
            ),
        )
        ctx.metadata["registry"] = registry

        ChainCompiler().compile(ctx)
        MCPCompiler().compile(ctx)

        names = set(ctx.tool_manifest.all_tool_names)
        assert "get_concept" in names
        assert "observe" in names  # Whole MCP is included

    def test_validation_passes(self):
        """Valid manifest should pass capability surface check."""
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Query stuff",
                domain_hints=["carton"],
            ),
        )
        ChainCompiler().compile(ctx)
        arm = MCPCompiler()
        arm.compile(ctx)
        report = arm.validate(ctx)
        assert report.aligned


class TestThreeArmPipeline:
    """Test the full Chain → Agent → MCP pipeline."""

    def test_full_pipeline_strict(self):
        """Strict pipeline with 3 filled arms should complete."""
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(),
            AgentConfigCompiler(),
            MCPCompiler(),
        ])
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Build a KG query agent",
                feature_type=FeatureType.AGENT,
                domain_hints=["carton"],
            ),
        )
        result = pipeline.compile(ctx)

        assert result.chain_plan is not None
        assert result.agent_profile is not None
        assert result.tool_manifest is not None
        assert "carton" in result.tool_manifest.all_tool_names
        assert result.alignment.aligned

    def test_full_pipeline_partial(self):
        """Partial pipeline shows Layer 3/3 with all arms filled."""
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(),
            AgentConfigCompiler(),
            MCPCompiler(),
        ])
        ctx = CompilationContext(
            task_spec=TaskSpec(description="test", domain_hints=["carton"]),
        )
        report = pipeline.compile_partial(ctx)

        assert report.layer == 3
        assert report.total == 3
        assert not report.not_implemented
        print(report)

    def test_context_freezes_to_compiled_agent(self):
        """After 3 arms, can freeze context to a CompiledAgent."""
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(),
            AgentConfigCompiler(),
            MCPCompiler(),
        ])
        ctx = CompilationContext(
            task_spec=TaskSpec(
                description="Test agent",
                domain_hints=["carton"],
            ),
        )
        pipeline.compile(ctx)

        agent = ctx.freeze()
        assert agent.task_spec.description == "Test agent"
        assert agent.chain_plan is not None
        assert agent.agent_profile is not None
        assert agent.tool_manifest is not None
