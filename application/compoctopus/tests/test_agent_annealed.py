"""Tests for the CompoctopusAgent annealed output.

These tests verify that the .octo file with #| pseudocode anneals
correctly to produce a working CompoctopusAgent implementation.

Tests cover:
1. Basic agent creation and properties
2. CompilerArm interface implementation  
3. Chain orchestration
4. Serialization methods
5. Edge cases from the spec
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from compoctopus.agent import CompoctopusAgent
from compoctopus.types import (
    ArmKind,
    TaskSpec,
    MermaidSpec,
    SystemPrompt,
    PromptSection,
    ToolManifest,
    CompiledAgent,
    GeometricAlignmentReport,
)
from compoctopus.context import CompilationContext


class TestCompoctopusAgentCreation:
    """Test basic agent creation and default values."""

    def test_create_with_name(self):
        agent = CompoctopusAgent(agent_name="test_agent")
        assert agent.name == "test_agent"

    def test_default_model(self):
        agent = CompoctopusAgent()
        assert agent.model == "minimax"

    def test_default_arm_kind_is_none(self):
        agent = CompoctopusAgent()
        assert agent.arm_kind is None

    def test_modules_default_empty_list(self):
        agent = CompoctopusAgent()
        assert agent.modules == []


class TestCompilerArmInterface:
    """Test that CompoctopusAgent implements CompilerArm interface."""

    def test_kind_property_returns_arm_kind(self):
        agent = CompoctopusAgent(arm_kind=ArmKind.AGENT)
        assert agent.kind == ArmKind.AGENT

    def test_kind_property_none_by_default(self):
        agent = CompoctopusAgent()
        assert agent.kind is None

    def test_get_mermaid_spec_returns_spec(self):
        spec = MermaidSpec()
        agent = CompoctopusAgent(mermaid_spec=spec)
        assert agent.get_mermaid_spec() is spec

    def test_get_mermaid_spec_returns_default_when_none(self):
        agent = CompoctopusAgent()
        result = agent.get_mermaid_spec()
        assert isinstance(result, MermaidSpec)

    def test_get_system_prompt_sections_returns_sections(self):
        sections = [PromptSection(tag="TEST", content="test content")]
        sp = SystemPrompt(sections=sections)
        agent = CompoctopusAgent(system_prompt=sp)
        assert agent.get_system_prompt_sections() == sections

    def test_get_system_prompt_sections_returns_empty_when_none(self):
        agent = CompoctopusAgent()
        assert agent.get_system_prompt_sections() == []

    def test_get_tool_surface_returns_manifest(self):
        manifest = ToolManifest()
        agent = CompoctopusAgent(tool_manifest=manifest)
        assert agent.get_tool_surface() is manifest

    def test_get_tool_surface_returns_default_when_none(self):
        agent = CompoctopusAgent()
        result = agent.get_tool_surface()
        assert isinstance(result, ToolManifest)


class TestNameProperty:
    """Test the name property."""

    def test_name_returns_agent_name(self):
        agent = CompoctopusAgent(agent_name="my_agent")
        assert agent.name == "my_agent"

    def test_name_returns_default_when_empty(self):
        agent = CompoctopusAgent(agent_name="")
        assert agent.name == "compoctopus_agent"

    def test_name_returns_default_when_none(self):
        agent = CompoctopusAgent()
        assert agent.name == "compoctopus_agent"


class TestExecuteMethod:
    """Test the async execute method."""

    @pytest.mark.asyncio
    async def test_execute_raises_when_no_chain(self):
        agent = CompoctopusAgent(agent_name="test")
        with pytest.raises(ValueError, match="has no chain"):
            await agent.execute()

    @pytest.mark.asyncio
    async def test_execute_calls_chain(self):
        mock_chain = AsyncMock()
        mock_chain.execute.return_value = {"result": "success"}
        
        agent = CompoctopusAgent(agent_name="test", chain=mock_chain)
        result = await agent.execute({})
        
        mock_chain.execute.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_execute_passes_context(self):
        mock_chain = AsyncMock()
        mock_chain.execute.return_value = {}
        
        agent = CompoctopusAgent(agent_name="test", chain=mock_chain)
        await agent.execute({"key": "value"})
        
        mock_chain.execute.assert_called_once_with({"key": "value"})

    @pytest.mark.asyncio
    async def test_execute_with_none_context(self):
        mock_chain = AsyncMock()
        mock_chain.execute.return_value = {}
        
        agent = CompoctopusAgent(agent_name="test", chain=mock_chain)
        await agent.execute()
        
        mock_chain.execute.assert_called_once_with({})


class TestCompileMethod:
    """Test the compile method."""

    def test_compile_runs_chain_and_updates_context(self):
        mock_chain = AsyncMock()
        mock_result = MagicMock()
        mock_result.context = {"output": "test_result", "extra": "data"}
        mock_chain.execute.return_value = mock_result
        
        agent = CompoctopusAgent(agent_name="test", chain=mock_chain)
        ctx = CompilationContext()
        ctx.task = "test_task"
        
        agent.compile(ctx)
        
        mock_chain.execute.assert_called_once()


class TestValidateMethod:
    """Test the validate method."""

    def test_validate_returns_geometric_alignment_report(self):
        agent = CompoctopusAgent(agent_name="test")
        ctx = CompilationContext()
        
        result = agent.validate(ctx)
        
        assert isinstance(result, GeometricAlignmentReport)

    def test_validate_with_system_prompt_and_mermaid(self):
        sp = SystemPrompt(sections=[
            PromptSection(tag="TEST", content="test")
        ])
        ms = MermaidSpec()
        
        agent = CompoctopusAgent(
            agent_name="test",
            system_prompt=sp,
            mermaid_spec=ms
        )
        ctx = CompilationContext()
        
        result = agent.validate(ctx)
        assert isinstance(result, GeometricAlignmentReport)


class TestDescribeMethod:
    """Test the describe method."""

    def test_describe_returns_string(self):
        agent = CompoctopusAgent(agent_name="test")
        desc = agent.describe()
        assert isinstance(desc, str)
        assert "test" in desc

    def test_describe_with_chain(self):
        from compoctopus.chain_ontology import Chain
        chain = Chain(chain_name="my_chain", links=[])
        agent = CompoctopusAgent(agent_name="test", chain=chain)
        
        desc = agent.describe()
        assert "chain=" in desc
        assert "my_chain" in desc

    def test_describe_with_depth(self):
        agent = CompoctopusAgent(agent_name="test")
        desc = agent.describe(depth=2)
        assert desc.startswith("    ")  # 2 levels of indent


class TestToSdnaMethod:
    """Test serialization to SDNA config."""

    def test_to_sdna_returns_dict(self):
        agent = CompoctopusAgent(agent_name="test", model="claude")
        sdna = agent.to_sdna()
        
        assert isinstance(sdna, dict)
        assert sdna["agent_name"] == "test"
        assert sdna["model"] == "claude"

    def test_to_sdna_includes_system_prompt(self):
        sp = SystemPrompt(sections=[
            PromptSection(tag="TEST", content="test content")
        ])
        agent = CompoctopusAgent(agent_name="test", system_prompt=sp)
        
        sdna = agent.to_sdna()
        assert "system_prompt" in sdna

    def test_to_sdna_includes_mermaid(self):
        ms = MermaidSpec()
        agent = CompoctopusAgent(agent_name="test", mermaid_spec=ms)
        
        sdna = agent.to_sdna()
        assert "mermaid_spec" in sdna

    def test_to_sdna_includes_chain_when_present(self):
        from compoctopus.chain_ontology import Chain, FunctionLink
        
        chain = Chain(chain_name="test_chain", links=[
            FunctionLink("step1", lambda ctx: ctx, "test step")
        ])
        agent = CompoctopusAgent(agent_name="test", chain=chain)
        
        sdna = agent.to_sdna()
        assert "chain" in sdna
        assert sdna["chain"]["name"] == "test_chain"

    def test_to_sdna_includes_modules(self):
        agent = CompoctopusAgent(agent_name="test", modules=["module1", "module2"])
        
        sdna = agent.to_sdna()
        assert sdna["modules"] == ["module1", "module2"]


class TestToLinkMethod:
    """Test to_link method."""

    def test_to_link_returns_self(self):
        agent = CompoctopusAgent(agent_name="test")
        assert agent.to_link() is agent


class TestFreezeMethod:
    """Test freeze to CompiledAgent."""

    def test_freeze_returns_compiled_agent(self):
        agent = CompoctopusAgent(agent_name="test", model="claude")
        compiled = agent.freeze()
        
        assert isinstance(compiled, CompiledAgent)
        assert compiled.agent_profile.name == "test"
        assert compiled.agent_profile.model == "claude"

    def test_freeze_with_task_spec(self):
        task_spec = TaskSpec(description="my task", feature_type=None)
        agent = CompoctopusAgent(agent_name="test", task_spec=task_spec)
        
        compiled = agent.freeze()
        assert compiled.task_spec.description == "my task"

    def test_freeze_with_system_prompt_and_tool_manifest(self):
        sp = SystemPrompt(sections=[
            PromptSection(tag="TEST", content="test")
        ])
        tm = ToolManifest()
        
        agent = CompoctopusAgent(
            agent_name="test",
            system_prompt=sp,
            tool_manifest=tm
        )
        
        compiled = agent.freeze()
        assert compiled.system_prompt is sp
        assert compiled.tool_manifest is tm


class TestRepr:
    """Test __repr__ method."""

    def test_repr_contains_name(self):
        agent = CompoctopusAgent(agent_name="test")
        assert "test" in repr(agent)

    def test_repr_contains_class_name(self):
        agent = CompoctopusAgent(agent_name="test")
        assert "CompoctopusAgent" in repr(agent)

    def test_repr_contains_model(self):
        agent = CompoctopusAgent(agent_name="test", model="claude")
        assert "claude" in repr(agent)

    def test_repr_with_chain(self):
        from compoctopus.chain_ontology import Chain
        chain = Chain(chain_name="my_chain", links=[])
        agent = CompoctopusAgent(agent_name="test", chain=chain)
        
        r = repr(agent)
        assert "my_chain" in r


class TestEdgeCases:
    """Test edge cases mentioned in the spec."""

    def test_chain_with_no_links(self):
        from compoctopus.chain_ontology import Chain
        chain = Chain(chain_name="empty", links=[])
        agent = CompoctopusAgent(agent_name="test", chain=chain)
        
        sdna = agent.to_sdna()
        assert len(sdna["chain"]["links"]) == 0

    def test_multiple_modules(self):
        agent = CompoctopusAgent(
            agent_name="test",
            modules=["mod1", "mod2", "mod3"]
        )
        assert len(agent.modules) == 3

    def test_empty_system_prompt_renders(self):
        sp = SystemPrompt()
        agent = CompoctopusAgent(agent_name="test", system_prompt=sp)
        
        rendered = sp.render()
        assert isinstance(rendered, str)

    def test_mermaid_spec_participants(self):
        ms = MermaidSpec()
        ms.add_participant("User")
        ms.add_participant("Agent")
        
        agent = CompoctopusAgent(agent_name="test", mermaid_spec=ms)
        spec = agent.get_mermaid_spec()
        
        assert "User" in spec.participants
        assert "Agent" in spec.participants
