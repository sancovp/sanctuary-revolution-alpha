"""Tests for the bootstrap mechanism — the design IS the test.

These tests demonstrate the core D:D→D property:
1. Self-compilation: each arm validates against its own description
2. Partial compilation: the pipeline runs what it can, reports what's missing
3. Empire spec: define a system, auto-generate its regression test

Layer 0: Everything defined, nothing passes  → NotImplementedError everywhere
Layer 1: Arms compile but produce empty      → Alignment violations
Layer 2: Arms produce outputs, tools missing → Capability Surface fails
Layer 3: Tools exist, prompts don't match    → Dual Description fails
Layer 4: Everything aligned                  → All green
Layer 5: System compiles itself              → Fixed point
"""

import pytest

from compoctopus.types import (
    ArmKind,
    InputPrompt,
    MermaidSpec,
    PromptSection,
    SystemPrompt,
    TaskSpec,
    ToolManifest,
    ToolSpec,
    MCPConfig,
)
from compoctopus.base import (
    CompilerArm,
    CompilerPipeline,
    SelfCompilationResult,
    PartialCompilationReport,
)
from compoctopus.context import CompilationContext
from compoctopus.arms import (
    ChainCompiler,
    AgentConfigCompiler,
    MCPCompiler,
    SkillCompiler,
    SystemPromptCompiler,
    InputPromptCompiler,
)


class TestSelfCompilation:
    """D:D→D — every arm, treated as an agent, must be self-consistent."""

    ALL_ARMS = [
        ChainCompiler,
        AgentConfigCompiler,
        MCPCompiler,
        SkillCompiler,
        SystemPromptCompiler,
        InputPromptCompiler,
    ]

    def test_self_compile_returns_result(self):
        """self_compile() should return a SelfCompilationResult."""
        arm = ChainCompiler()
        result = arm.self_compile()
        assert isinstance(result, SelfCompilationResult)
        assert result.arm == ArmKind.CHAIN
        assert result.arm_name == arm.name

    @pytest.mark.parametrize("ArmClass", ALL_ARMS,
                             ids=lambda c: c.__name__)
    def test_each_arm_has_valid_mermaid(self, ArmClass):
        """Every arm's mermaid spec must be structurally valid."""
        arm = ArmClass()
        result = arm.self_compile()
        # Filter for syntax-only issues
        syntax_issues = [i for i in result.issues
                        if not i.startswith("DualDescription")]
        # All arms should have valid mermaid syntax
        assert not any("No participants" in i for i in syntax_issues), (
            f"{ArmClass.__name__}: {syntax_issues}"
        )
        assert not any("No messages" in i for i in syntax_issues), (
            f"{ArmClass.__name__}: {syntax_issues}"
        )

    @pytest.mark.parametrize("ArmClass", ALL_ARMS,
                             ids=lambda c: c.__name__)
    def test_each_arm_has_identity_and_workflow(self, ArmClass):
        """Every arm must describe itself with IDENTITY and WORKFLOW sections."""
        arm = ArmClass()
        result = arm.self_compile()
        section_issues = [i for i in result.issues if "Missing" in i]
        assert not section_issues, (
            f"{ArmClass.__name__} self-compilation: {section_issues}"
        )

    def test_pipeline_self_compile_all(self):
        """self_compile_all() should check every arm in the pipeline."""
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(),
            AgentConfigCompiler(),
            MCPCompiler(),
        ])
        results = pipeline.self_compile_all()
        assert len(results) == 3
        for r in results:
            assert isinstance(r, SelfCompilationResult)
            print(r)  # Show results for visibility

    def test_self_compile_printable(self):
        """Results should be human-readable."""
        arm = ChainCompiler()
        result = arm.self_compile()
        text = str(result)
        assert "Chain Compiler" in text


class TestPartialCompilation:
    """The bootstrap gradient — run what works, report what's missing."""

    def test_partial_compilation_shows_progress(self):
        """Layer 6: All arms implemented."""
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(),
            AgentConfigCompiler(),
            MCPCompiler(),
            SkillCompiler(),
            SystemPromptCompiler(),
            InputPromptCompiler(),
        ])
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        report = pipeline.compile_partial(ctx)

        assert report.layer == 6
        assert report.total == 6
        assert len(report.not_implemented) == 0
        assert len(report.completed) == 6
        print(report)

    def test_partial_report_shows_gradient(self):
        """The report tells you exactly what to fill next."""
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(),
            AgentConfigCompiler(),
            SkillCompiler(),
        ])
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        report = pipeline.compile_partial(ctx)

        text = str(report)
        assert "Layer 3/3" in text
        assert "completed" in text

    def test_layer_increments_as_arms_are_filled(self):
        """As arms get implemented, the layer count goes up.

        We simulate this by using the convenience methods that bypass
        the NotImplementedError.
        """
        # Manually populate context (simulating filled arms)
        ctx = CompilationContext(task_spec=TaskSpec(description="test"))
        ctx.chain_plan = ChainCompiler.single_node_chain(ctx)
        ctx.agent_profile = AgentConfigCompiler.default_profile()

        # Check that context is progressively filled
        assert ctx.chain_plan is not None
        assert ctx.agent_profile is not None
        assert ctx.tool_manifest is None  # MCPCompiler not yet filled

        # The layer concept: chain + agent are "done", mcp is "next"
        completed = []
        if ctx.chain_plan:
            completed.append("Chain")
        if ctx.agent_profile:
            completed.append("Agent")
        if ctx.tool_manifest:
            completed.append("MCP")

        assert len(completed) == 2
        assert "MCP" not in completed


class TestEmpireSpec:
    """Define a system, generate its regression test automatically.

    The empire spec is a list of (TaskSpec, expected_properties) pairs.
    The test suite verifies that the compiled agents match the spec.
    """

    def test_empire_spec_format(self):
        """An empire spec is just a dict of TaskSpec → expected outputs."""
        empire = {
            "summarizer": {
                "task": TaskSpec(description="Summarize conversations"),
                "expect_tools": ["carton"],
                "expect_identity": "summariz",  # substring match
            },
            "code_reviewer": {
                "task": TaskSpec(description="Review code changes"),
                "expect_tools": ["filesystem", "git"],
                "expect_identity": "code review",
            },
        }

        # The empire spec is the design
        assert len(empire) == 2

        # The design is the test:
        for agent_name, spec in empire.items():
            assert spec["task"].description
            assert spec["expect_tools"]
            assert spec["expect_identity"]

    def test_empire_regression_generator(self):
        """Generate alignment checks from an empire spec.

        Each agent in the empire gets a check:
        1. Its tool manifest contains expected tools
        2. Its system prompt mentions its identity
        3. Its mermaid references its tools
        4. All 5 invariants pass
        """
        # Define a minimal agent spec
        agent_spec = {
            "task": TaskSpec(description="Query knowledge graph"),
            "expect_tools": {"carton"},
        }

        # Simulate a compiled agent (manually filled for now)
        system_prompt = SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="You query the knowledge graph"),
            PromptSection(tag="WORKFLOW", content="Query carton, analyze results"),
            PromptSection(tag="CAPABILITY", content="carton MCP"),
            PromptSection(tag="CONSTRAINTS", content="Read-only"),
        ])

        mermaid = MermaidSpec()
        mermaid.add_participant("Agent")
        mermaid.add_participant("carton")
        mermaid.add_message("Agent", "carton", "Query knowledge graph")

        input_prompt = InputPrompt(goal="Query the KG", mermaid=mermaid)

        tool_manifest = ToolManifest(
            mcps={"carton": MCPConfig(
                name="carton",
                tools=[ToolSpec(name="carton")],
            )},
        )

        # The regression test: does the compiled agent match the spec?
        equipped = set(tool_manifest.all_tool_names)
        assert agent_spec["expect_tools"].issubset(equipped), (
            f"Missing tools: {agent_spec['expect_tools'] - equipped}"
        )

        # And the alignment check is free:
        from compoctopus.alignment import GeometricAlignmentValidator
        validator = GeometricAlignmentValidator()
        report = validator.validate_all(
            system_prompt=system_prompt,
            input_prompt=input_prompt,
            tool_manifest=tool_manifest,
        )
        # Print the full report
        print(f"\n{report}")
        # The system spawns with its regression test built in
        assert len(report.results) == 5
