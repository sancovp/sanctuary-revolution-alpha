"""Tests for Phase 1: MermaidSpec graph-first builder, parser, and alignment validators."""

import pytest

from compoctopus.types import (
    AlignmentResult,
    GeometricAlignmentReport,
    GeometricInvariant,
    InputPrompt,
    MCPConfig,
    MermaidSpec,
    PromptSection,
    SystemPrompt,
    ToolManifest,
    ToolSpec,
    TrustLevel,
)
from compoctopus.mermaid import (
    MermaidGenerator,
    MermaidParser,
    MermaidValidator,
    extract_tool_references_from_text,
)
from compoctopus.alignment import GeometricAlignmentValidator


class TestMermaidSpecBuilder:
    """Test the graph-first MermaidSpec builder API."""

    def test_empty_spec(self):
        spec = MermaidSpec()
        assert spec.participants == []
        assert spec.task_list == []
        assert spec.tool_references == []
        assert spec.branch_points == []
        assert "sequenceDiagram" in spec.diagram

    def test_add_participants(self):
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant("Agent", "My Agent")
        assert spec.participants == ["User", "Agent"]
        assert "participant User" in spec.diagram
        assert "participant Agent as My Agent" in spec.diagram

    def test_add_messages(self):
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant("Agent")
        spec.add_message("User", "Agent", "Hello")
        spec.add_message("Agent", "User", "Response")
        assert "User->>Agent: Hello" in spec.diagram
        assert "Agent->>User: Response" in spec.diagram
        assert spec.task_list == ["Hello", "Response"]

    def test_tool_references(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_participant("Carton")
        spec.add_participant("Registry")
        spec.add_message("Agent", "Carton", "Query")
        spec.add_message("Agent", "Registry", "Lookup")
        # Self-messages should NOT be tool refs
        spec.add_message("Agent", "Agent", "Think")
        refs = spec.tool_references
        assert "Carton" in refs
        assert "Registry" in refs
        assert "Agent" not in refs  # Self-message excluded

    def test_alt_block(self):
        spec = MermaidSpec()
        spec.add_participant("A")
        spec.add_participant("B")
        spec.add_alt([
            ("Success", [("A", "B", "Result")]),
            ("Failure", [("A", "A", "Handle error")]),
        ])
        diag = spec.diagram
        assert "alt Success" in diag
        assert "else Failure" in diag
        assert "end" in diag
        assert spec.branch_points == ["Success vs Failure"]

    def test_loop_block(self):
        spec = MermaidSpec()
        spec.add_participant("A")
        spec.add_participant("B")
        spec.add_loop("For each item", [
            ("A", "B", "Process"),
            ("B", "A", "Result"),
        ])
        diag = spec.diagram
        assert "loop For each item" in diag
        assert "end" in diag
        # Loop should NOT appear in branch_points
        assert spec.branch_points == []

    def test_fluent_api(self):
        """Builder methods should return self for chaining."""
        spec = (
            MermaidSpec()
            .add_participant("User")
            .add_participant("Agent")
            .add_message("User", "Agent", "Hello")
        )
        assert len(spec.participants) == 2
        assert len(spec.task_list) == 1

    def test_arm_mermaid_specs_render(self):
        """All 6 arms should produce valid mermaid diagrams."""
        from compoctopus.arms import (
            ChainCompiler, AgentConfigCompiler, MCPCompiler,
            SkillCompiler, SystemPromptCompiler, InputPromptCompiler,
        )
        for ArmClass in [ChainCompiler, AgentConfigCompiler, MCPCompiler,
                         SkillCompiler, SystemPromptCompiler, InputPromptCompiler]:
            arm = ArmClass()
            spec = arm.get_mermaid_spec()
            diag = spec.diagram
            assert diag.startswith("sequenceDiagram"), f"{ArmClass.__name__}"
            assert "participant" in diag, f"{ArmClass.__name__} missing participants"
            assert len(spec.task_list) > 0, f"{ArmClass.__name__} empty task_list"


class TestMermaidParser:
    """Test the mermaid text → MermaidSpec parser."""

    def test_round_trip_simple(self):
        """Build a spec, render it, parse it back — should match."""
        original = MermaidSpec()
        original.add_participant("User")
        original.add_participant("Agent")
        original.add_message("User", "Agent", "Hello")
        original.add_message("Agent", "User", "World")

        text = original.diagram
        parser = MermaidParser()
        parsed = parser.parse(text)

        assert parsed.participants == original.participants
        assert parsed.task_list == original.task_list

    def test_parse_with_fences(self):
        text = """```mermaid
sequenceDiagram
    participant User
    participant Agent
    User->>Agent: Task
```"""
        parser = MermaidParser()
        spec = parser.parse(text)
        assert spec.participants == ["User", "Agent"]
        assert spec.task_list == ["Task"]

    def test_parse_alt_block(self):
        text = """
sequenceDiagram
    participant A
    participant B
    A->>B: Request
    alt Success
        B->>A: OK
    else Failure
        B->>A: Error
    end
"""
        parser = MermaidParser()
        spec = parser.parse(text)
        assert spec.participants == ["A", "B"]
        assert spec.branch_points == ["Success vs Failure"]

    def test_parse_loop_block(self):
        text = """
sequenceDiagram
    participant A
    participant B
    loop Process items
        A->>B: Process
        B->>A: Result
    end
"""
        parser = MermaidParser()
        spec = parser.parse(text)
        assert "Process" in spec.task_list

    def test_round_trip_arm_specs(self):
        """Every arm's mermaid spec should survive a round trip."""
        from compoctopus.arms import ChainCompiler, MCPCompiler
        parser = MermaidParser()

        for ArmClass in [ChainCompiler, MCPCompiler]:
            arm = ArmClass()
            original = arm.get_mermaid_spec()
            text = original.diagram
            parsed = parser.parse(text)
            # Participants should match
            assert set(parsed.participants) == set(original.participants), (
                f"{ArmClass.__name__} round-trip lost participants"
            )


class TestMermaidGenerator:
    """Test context-driven mermaid generation."""

    def test_for_agent_basic(self):
        gen = MermaidGenerator()
        spec = gen.for_agent(
            agent_name="Summarizer",
            tool_names=["carton", "filesystem"],
            workflow_steps=["Analyze conversation", "Generate summary"],
        )
        diag = spec.diagram
        assert "participant Summarizer" in diag
        assert "participant carton" in diag
        assert "participant filesystem" in diag
        assert "Analyze conversation" in diag
        # Check tool references include the tools
        assert "carton" in spec.tool_references
        assert "filesystem" in spec.tool_references

    def test_for_pipeline(self):
        gen = MermaidGenerator()
        spec = gen.for_pipeline(
            arm_names=["Chain", "Agent", "MCP"],
            task_label="Summarize conversations",
        )
        diag = spec.diagram
        assert "participant Router" in diag
        assert "Run Chain" in diag
        assert "Run Agent" in diag
        assert "Run MCP" in diag
        assert "Validate alignment" in diag


class TestMermaidValidator:
    """Test diagram validation against tool surfaces."""

    def test_no_violations_when_aligned(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_participant("carton")
        spec.add_message("Agent", "carton", "Query")

        validator = MermaidValidator()
        violations = validator.check_tool_coverage(spec, {"carton"})
        assert violations == []

    def test_phantom_tool_detected(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_participant("carton")
        spec.add_message("Agent", "carton", "Query")

        validator = MermaidValidator()
        violations = validator.check_tool_coverage(spec, set())  # No tools equipped
        assert any("PHANTOM TOOL" in v for v in violations)

    def test_orphaned_tool_detected(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_message("Agent", "Agent", "Think")

        validator = MermaidValidator()
        violations = validator.check_tool_coverage(spec, {"carton"})
        assert any("ORPHANED TOOL" in v for v in violations)

    def test_syntax_validation(self):
        validator = MermaidValidator()
        empty_spec = MermaidSpec()
        violations = validator.check_syntax(empty_spec)
        assert any("no participants" in v for v in violations)


class TestAlignmentValidator:
    """Test the 5 geometric invariant validators."""

    def _make_aligned_system(self):
        """Create a minimal aligned system for testing."""
        system_prompt = SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="Test agent"),
            PromptSection(tag="WORKFLOW", content=(
                "1. Query the knowledge graph\n"
                "2. Analyze results\n"
                "3. Generate summary"
            )),
            PromptSection(tag="CAPABILITY", content=(
                "You have access to:\n"
                "- carton MCP (query knowledge graph)"
            )),
            PromptSection(tag="CONSTRAINTS", content="Read-only operations"),
        ])

        mermaid = MermaidSpec()
        mermaid.add_participant("Agent")
        mermaid.add_participant("carton")
        mermaid.add_message("Agent", "carton", "Query knowledge graph")
        mermaid.add_message("Agent", "Agent", "Analyze results")

        input_prompt = InputPrompt(
            goal="Summarize conversations",
            mermaid=mermaid,
        )

        tool_manifest = ToolManifest(
            mcps={"carton": MCPConfig(
                name="carton",
                tools=[ToolSpec(name="carton")],
            )},
        )

        return system_prompt, input_prompt, tool_manifest

    def test_dual_description_pass(self):
        sp, ip, _ = self._make_aligned_system()
        validator = GeometricAlignmentValidator()
        result = validator.check_dual_description(sp, ip)
        assert result.passed, f"Violations: {result.violations}"

    def test_dual_description_fail_missing_workflow(self):
        sp = SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="Test"),
        ])
        ip = InputPrompt(goal="test", mermaid=MermaidSpec())
        validator = GeometricAlignmentValidator()
        result = validator.check_dual_description(sp, ip)
        assert not result.passed
        assert any("WORKFLOW" in v for v in result.violations)

    def test_capability_surface_pass(self):
        sp, ip, tm = self._make_aligned_system()
        validator = GeometricAlignmentValidator()
        result = validator.check_capability_surface(sp, ip, tm)
        assert result.passed, f"Violations: {result.violations}"

    def test_capability_surface_phantom(self):
        """Referencing a tool that isn't equipped → phantom."""
        sp, ip, _ = self._make_aligned_system()
        empty_manifest = ToolManifest()  # No tools equipped
        validator = GeometricAlignmentValidator()
        result = validator.check_capability_surface(sp, ip, empty_manifest)
        assert not result.passed
        assert any("PHANTOM" in v for v in result.violations)

    def test_trust_boundary_observer(self):
        """OBSERVER trust with write tools → violation."""
        tool_manifest = ToolManifest(
            local_tools=[
                ToolSpec(name="read_file"),
                ToolSpec(name="edit_file"),  # Write tool!
            ],
        )
        sp = SystemPrompt(sections=[
            PromptSection(tag="CONSTRAINTS", content="Read-only"),
        ])
        validator = GeometricAlignmentValidator()
        result = validator.check_trust_boundary(
            tool_manifest, TrustLevel.OBSERVER, sp
        )
        assert not result.passed
        assert any("edit_file" in v for v in result.violations)

    def test_trust_boundary_executor_tool_count(self):
        """EXECUTOR trust with too many tools → violation."""
        tools = [ToolSpec(name=f"tool_{i}") for i in range(10)]
        tool_manifest = ToolManifest(local_tools=tools)
        sp = SystemPrompt(sections=[
            PromptSection(tag="CONSTRAINTS", content="Limited"),
        ])
        validator = GeometricAlignmentValidator()
        result = validator.check_trust_boundary(
            tool_manifest, TrustLevel.EXECUTOR, sp
        )
        assert not result.passed
        assert any("exceeds" in v for v in result.violations)

    def test_polymorphic_dispatch_valid(self):
        validator = GeometricAlignmentValidator()
        result = validator.check_polymorphic_dispatch(
            "agent", ["agent", "tool", "chain"]
        )
        assert result.passed

    def test_polymorphic_dispatch_unknown_type(self):
        validator = GeometricAlignmentValidator()
        result = validator.check_polymorphic_dispatch(
            "nonexistent", ["agent", "tool"]
        )
        assert not result.passed

    def test_validate_all(self):
        """Full 5-invariant validation should produce a complete report."""
        sp, ip, tm = self._make_aligned_system()
        validator = GeometricAlignmentValidator()
        report = validator.validate_all(
            system_prompt=sp,
            input_prompt=ip,
            tool_manifest=tm,
            trust_level=TrustLevel.BUILDER,
            feature_type="agent",
            available_paths=["agent"],
        )
        assert len(report.results) == 5
        # Print report for visibility
        print(report)
