"""Tests for mock tool generation — the bootstrap enabler.

Mock tools let the entire pipeline run end-to-end before real tools exist.
The mocks have the same interface, so the regression test works from day zero.
"""

import pytest

from compoctopus.mock import (
    MockHeavenTool,
    MockToolSpec,
    auto_mock_from_empire,
    auto_mock_from_mermaid,
    auto_mock_manifest,
    make_mock_tool,
)
from compoctopus.types import (
    MermaidSpec,
    TaskSpec,
    ToolManifest,
)


class TestMakeMockTool:
    """Test the core generator function."""

    def test_basic_creation(self):
        mock = make_mock_tool("EssayTool", ["intro", "body", "conclusion"])
        assert mock.name == "EssayTool"
        assert mock.tool_params == ["intro", "body", "conclusion"]

    def test_call_returns_formatted_string(self):
        mock = make_mock_tool("EssayTool", ["intro", "body", "conclusion"])
        result = mock(intro="Opening", body="Main point", conclusion="Summary")
        assert "EssayTool(" in result
        assert "intro='Opening'" in result
        assert "body='Main point'" in result
        assert "conclusion='Summary'" in result

    def test_passthrough_typing(self):
        """All params are str — typed passthrough."""
        mock = make_mock_tool("MyTool", ["query", "context"])
        # Should accept any string
        result = mock(query="find X", context="in repo Y")
        assert isinstance(result, str)
        assert "MyTool(" in result

    def test_empty_params(self):
        mock = make_mock_tool("NoArgsTool", [])
        result = mock()
        assert result == "NoArgsTool()"

    def test_auto_description(self):
        mock = make_mock_tool("QueryTool", ["query"])
        assert "QueryTool" in mock.description
        assert "query" in mock.description

    def test_custom_description(self):
        mock = make_mock_tool(
            "QueryTool", ["query"],
            description="Custom desc for QueryTool"
        )
        assert mock.description == "Custom desc for QueryTool"

    def test_args_schema(self):
        mock = make_mock_tool("EssayTool", ["intro", "body", "conclusion"])
        assert "intro" in mock.tool_arguments
        assert mock.tool_arguments["intro"]["type"] == "string"
        assert mock.tool_arguments["intro"]["required"] is True


class TestAutoMockFromMermaid:
    """Test mermaid → mock tool generation."""

    def test_generates_mocks_for_tool_refs(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_participant("carton")
        spec.add_participant("filesystem")
        spec.add_message("Agent", "carton", "Query")
        spec.add_message("Agent", "filesystem", "Read")

        mocks = auto_mock_from_mermaid(spec)
        names = {m.name for m in mocks}
        assert "carton" in names
        assert "filesystem" in names

    def test_excludes_specified_tools(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_participant("carton")
        spec.add_participant("internal")
        spec.add_message("Agent", "carton", "Query")
        spec.add_message("Agent", "internal", "Process")

        mocks = auto_mock_from_mermaid(spec, exclude={"internal"})
        names = {m.name for m in mocks}
        assert "carton" in names
        assert "internal" not in names

    def test_mocks_are_callable(self):
        spec = MermaidSpec()
        spec.add_participant("Agent")
        spec.add_participant("carton")
        spec.add_message("Agent", "carton", "Query KG")

        mocks = auto_mock_from_mermaid(spec)
        for mock in mocks:
            result = mock(input="test query")
            assert isinstance(result, str)
            assert mock.name in result


class TestAutoMockManifest:
    """Test tool names → ToolManifest generation."""

    def test_creates_valid_manifest(self):
        manifest = auto_mock_manifest(["carton", "filesystem", "git"])
        assert isinstance(manifest, ToolManifest)
        all_tools = manifest.all_tool_names
        assert "carton" in all_tools
        assert "filesystem" in all_tools
        assert "git" in all_tools

    def test_custom_params(self):
        manifest = auto_mock_manifest(
            ["EssayTool"],
            params_per_tool={"EssayTool": ["intro", "body", "conclusion"]},
        )
        assert "EssayTool" in manifest.all_tool_names
        # The mock should be accessible
        assert hasattr(manifest, "_mocks")
        mock = manifest._mocks["EssayTool"]
        result = mock(intro="Hi", body="World", conclusion="Bye")
        assert "EssayTool(" in result

    def test_manifest_passes_alignment(self):
        """A mock manifest should pass capability surface validation."""
        from compoctopus.alignment import GeometricAlignmentValidator
        from compoctopus.types import (
            InputPrompt, SystemPrompt, PromptSection, MermaidSpec,
        )

        # Build aligned system using mocks
        tools = ["carton", "filesystem"]
        manifest = auto_mock_manifest(tools)

        mermaid = MermaidSpec()
        mermaid.add_participant("Agent")
        for t in tools:
            mermaid.add_participant(t)
            mermaid.add_message("Agent", t, f"Use {t}")

        input_prompt = InputPrompt(
            goal="Do the thing",
            mermaid=mermaid,
        )

        system_prompt = SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="Test agent"),
            PromptSection(tag="WORKFLOW", content="Use carton and filesystem"),
            PromptSection(tag="CAPABILITY", content="carton, filesystem"),
            PromptSection(tag="CONSTRAINTS", content="Read-only"),
        ])

        validator = GeometricAlignmentValidator()
        result = validator.check_capability_surface(
            system_prompt, input_prompt, manifest
        )
        assert result.passed, f"Violations: {result.violations}"


class TestAutoMockFromEmpire:
    """Test empire spec → manifest generation."""

    def test_creates_manifests_for_each_agent(self):
        empire = {
            "summarizer": {
                "task": TaskSpec(description="Summarize"),
                "expect_tools": ["carton"],
            },
            "reviewer": {
                "task": TaskSpec(description="Review code"),
                "expect_tools": ["filesystem", "git"],
            },
        }

        manifests = auto_mock_from_empire(empire)
        assert "summarizer" in manifests
        assert "reviewer" in manifests
        assert "carton" in manifests["summarizer"].all_tool_names
        assert "filesystem" in manifests["reviewer"].all_tool_names
        assert "git" in manifests["reviewer"].all_tool_names

    def test_empire_with_typed_params(self):
        empire = {
            "writer": {
                "task": TaskSpec(description="Write essay"),
                "expect_tools": ["EssayTool"],
                "tool_params": {
                    "EssayTool": ["intro", "body1", "body2", "conclusion"],
                },
            },
        }

        manifests = auto_mock_from_empire(empire)
        manifest = manifests["writer"]
        assert "EssayTool" in manifest.all_tool_names
        # Call the mock
        mock = manifest._mocks["EssayTool"]
        result = mock(
            intro="Hello",
            body1="First point",
            body2="Second point",
            conclusion="Goodbye",
        )
        assert "EssayTool(" in result
        assert "body1='First point'" in result
        assert "body2='Second point'" in result


class TestEndToEndBootstrap:
    """The whole game: design → mock → validate → regression test."""

    def test_design_to_regression(self):
        """Design an agent, mock its tools, validate all invariants.

        This is the proof: the system spawns with 100% regression.
        """
        from compoctopus.alignment import GeometricAlignmentValidator
        from compoctopus.types import InputPrompt, SystemPrompt, PromptSection

        # 1. DESIGN: Define the agent
        design = {
            "name": "KnowledgeAgent",
            "tools": ["carton", "chroma_query"],
            "tool_params": {
                "carton": ["concept_name"],
                "chroma_query": ["query", "k"],
            },
            "workflow": [
                "Search knowledge base with chroma_query",
                "Retrieve concept details from carton",
                "Synthesize findings",
            ],
        }

        # 2. MOCK: Generate mocked tools
        manifest = auto_mock_manifest(
            design["tools"],
            params_per_tool=design["tool_params"],
        )

        # Verify mocks work
        carton_mock = manifest._mocks["carton"]
        assert "carton(concept_name='TestConcept')" == carton_mock(
            concept_name="TestConcept"
        )

        chroma_mock = manifest._mocks["chroma_query"]
        assert "chroma_query(" in chroma_mock(query="test", k="5")

        # 3. BUILD: Assemble the agent description
        mermaid = MermaidSpec()
        mermaid.add_participant("Agent", design["name"])
        for tool in design["tools"]:
            mermaid.add_participant(tool)

        for step in design["workflow"]:
            # Find which tool this step references
            used_tool = None
            for tool in design["tools"]:
                if tool in step.lower():
                    used_tool = tool
                    break
            if used_tool:
                mermaid.add_message("Agent", used_tool, step)
            else:
                mermaid.add_message("Agent", "Agent", step)

        system_prompt = SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content=f"You are the {design['name']}.",
            ),
            PromptSection(
                tag="WORKFLOW",
                content="\n".join(
                    f"{i+1}. {s}" for i, s in enumerate(design["workflow"])
                ),
            ),
            PromptSection(
                tag="CAPABILITY",
                content="You have access to:\n" + "\n".join(
                    f"- {t}" for t in design["tools"]
                ),
            ),
            PromptSection(tag="CONSTRAINTS", content="Read-only operations"),
        ])

        input_prompt = InputPrompt(goal="Query the KG", mermaid=mermaid)

        # 4. VALIDATE: Run all 5 invariants
        validator = GeometricAlignmentValidator()
        report = validator.validate_all(
            system_prompt=system_prompt,
            input_prompt=input_prompt,
            tool_manifest=manifest,
            feature_type="agent",
            available_paths=["agent"],
        )

        # Print as proof
        print(f"\n{report}")

        # 5. THE WHOLE GAME: all 5 invariants pass from day zero
        for result in report.results:
            assert result.passed, (
                f"{result.invariant.value} FAILED: {result.violations}"
            )
