"""Tests for CompoctopusAgent — Chain-based architecture.

Tests the Chain/EvalChain/Dovetail architecture for 🐙 Coder and Planner.
No state machines. All orchestration is via SDNA Chains.
"""

import pytest

from compoctopus.chain_ontology import Chain, EvalChain, FunctionLink, ConfigLink, Link
from compoctopus.octopus_coder import (
    CompoctopusAgent,
    make_octopus_coder,
    make_planner,
)


# =============================================================================
# CompoctopusAgent base type
# =============================================================================

class TestCompoctopusAgent:
    """Test the abstract agent type."""

    def test_basic_creation(self):
        agent = CompoctopusAgent(agent_name="test")
        assert agent.name == "test"
        assert agent.model == "minimax"

    def test_freeze(self):
        agent = CompoctopusAgent(agent_name="test", model="claude")
        compiled = agent.freeze()
        assert compiled.agent_profile.name == "test"
        assert compiled.agent_profile.model == "claude"

    def test_describe_with_chain(self):
        chain = Chain(chain_name="test_chain", links=[])
        agent = CompoctopusAgent(agent_name="test", chain=chain)
        desc = agent.describe()
        assert "test" in desc
        assert "chain=" in desc

    def test_repr(self):
        agent = CompoctopusAgent(agent_name="test")
        assert "CompoctopusAgent" in repr(agent)

    @pytest.mark.asyncio
    async def test_execute_requires_chain(self):
        agent = CompoctopusAgent(agent_name="test")
        with pytest.raises(ValueError, match="has no chain"):
            await agent.execute()

    def test_to_sdna_with_chain(self):
        chain = Chain(chain_name="test_chain", links=[
            FunctionLink("step1", lambda ctx: ctx, "test step"),
        ])
        agent = CompoctopusAgent(agent_name="test", chain=chain, model="claude")
        sdna = agent.to_sdna()
        assert sdna["agent_name"] == "test"
        assert sdna["model"] == "claude"
        assert "chain" in sdna
        assert sdna["chain"]["name"] == "test_chain"
        assert sdna["chain"]["type"] == "Chain"
        assert len(sdna["chain"]["links"]) == 1

    def test_to_link_returns_self(self):
        agent = CompoctopusAgent(agent_name="test")
        assert agent.to_link() is agent


# =============================================================================
# 🐙 Coder — EvalChain architecture
# =============================================================================

class TestOctoCoderChainArchitecture:
    """Test the 🐙 Coder's Chain-based architecture."""

    def test_has_chain(self):
        coder = make_octopus_coder()
        assert coder.chain is not None

    def test_chain_is_eval_chain(self):
        coder = make_octopus_coder()
        assert isinstance(coder.chain, EvalChain)

    def test_chain_has_evaluator(self):
        coder = make_octopus_coder()
        assert coder.chain.evaluator is not None
        assert coder.chain.evaluator.name == "verify"

    def test_chain_has_4_flow_links(self):
        """stub, pseudo, tests, anneal — then verify as evaluator."""
        coder = make_octopus_coder()
        assert len(coder.chain.links) == 4

    def test_chain_link_names(self):
        coder = make_octopus_coder()
        names = [link.name for link in coder.chain.links]
        assert names == ["stub", "pseudo", "tests", "anneal"]

    def test_llm_phases_are_links(self):
        """LLM phases are SDNACs (with SDNA) or ConfigLinks (without)."""
        coder = make_octopus_coder()
        for link in coder.chain.links[:3]:  # stub, pseudo, tests
            assert hasattr(link, 'name'), f"{link} should have name"
            assert hasattr(link, 'execute'), f"{link.name} should be executable"

    def test_mechanical_steps_are_function_links(self):
        coder = make_octopus_coder()
        anneal = coder.chain.links[3]
        verify = coder.chain.evaluator
        assert isinstance(anneal, FunctionLink)
        assert isinstance(verify, FunctionLink)

    def test_chain_has_dovetails(self):
        """3 dovetails between 4 links."""
        coder = make_octopus_coder()
        assert len(coder.chain.dovetails) == 3

    def test_dovetail_names(self):
        coder = make_octopus_coder()
        names = [d.name for d in coder.chain.dovetails]
        assert names == ["stub_to_pseudo", "pseudo_to_tests", "tests_to_anneal"]

    def test_dovetail_expected_outputs(self):
        coder = make_octopus_coder()
        # stub → pseudo: expects octo_path
        assert "octo_path" in coder.chain.dovetails[0].expected_outputs
        # tests → anneal: expects octo_path AND test_path
        assert "octo_path" in coder.chain.dovetails[2].expected_outputs
        assert "test_path" in coder.chain.dovetails[2].expected_outputs

    def test_max_cycles(self):
        coder = make_octopus_coder()
        assert coder.chain.max_cycles == 5

    def test_describe_shows_chain(self):
        coder = make_octopus_coder()
        desc = coder.describe()
        assert "chain=" in desc
        assert "octopus_coder" in desc
        assert "EvalChain" in desc

    def test_has_system_prompt(self):
        coder = make_octopus_coder()
        assert coder.system_prompt is not None
        rendered = coder.system_prompt.render()
        assert "🐙" in rendered
        assert "#>> STUB" in rendered

    def test_no_state_machine(self):
        """State machines are dead. Only chains."""
        coder = make_octopus_coder()
        assert not hasattr(coder, 'state_machine')

    def test_sdnac_has_config(self):
        """Each SDNAC/ConfigLink carries config."""
        coder = make_octopus_coder()
        for link in coder.chain.links[:3]:
            config = getattr(link, 'config', None)
            assert config is not None, f"{link.name} should have config"

    def test_sdnac_has_system_prompt(self):
        coder = make_octopus_coder()
        for link in coder.chain.links[:3]:
            config = getattr(link, 'config', None)
            if config and hasattr(config, 'system_prompt'):
                assert config.system_prompt


# =============================================================================
# Planner — Chain architecture
# =============================================================================

class TestPlannerChainArchitecture:
    """Test the Planner's Chain-based architecture."""

    def test_has_chain(self):
        planner = make_planner()
        assert planner.chain is not None

    def test_chain_is_plain_chain(self):
        """Planner is a Chain, not EvalChain (no loops)."""
        planner = make_planner()
        assert isinstance(planner.chain, Chain)
        assert not isinstance(planner.chain, EvalChain)

    def test_chain_has_5_links(self):
        """PROJECT, FEATURE, COMPONENT, DELIVERABLE, TASK."""
        planner = make_planner()
        assert len(planner.chain.links) == 5

    def test_chain_link_names(self):
        planner = make_planner()
        names = [link.name for link in planner.chain.links]
        # With SDNA: planner_project, planner_feature, ...
        # Without SDNA: project, feature, ...
        expected_suffixes = ["project", "feature", "component", "deliverable", "task"]
        for name, suffix in zip(names, expected_suffixes):
            assert name.endswith(suffix), f"Link name '{name}' should end with '{suffix}'"

    def test_chain_has_dovetails(self):
        """4 dovetails between 5 links."""
        planner = make_planner()
        assert len(planner.chain.dovetails) == 4

    def test_dovetail_names(self):
        planner = make_planner()
        names = [d.name for d in planner.chain.dovetails]
        assert names == [
            "project_to_feature",
            "feature_to_component",
            "component_to_deliverable",
            "deliverable_to_task",
        ]

    def test_dovetail_expected_outputs(self):
        planner = make_planner()
        # project → feature: expects project_id
        assert "project_id" in planner.chain.dovetails[0].expected_outputs
        # deliverable → task: expects hierarchy
        assert "hierarchy" in planner.chain.dovetails[3].expected_outputs

    def test_all_links_are_executable(self):
        """All GIINT phases are SDNACs or ConfigLinks — both executable."""
        planner = make_planner()
        for link in planner.chain.links:
            assert hasattr(link, 'execute'), f"{link.name} should be executable"
            assert hasattr(link, 'name'), f"{link} should have name"

    def test_describe_shows_chain(self):
        planner = make_planner()
        desc = planner.describe()
        assert "chain=" in desc
        assert "planner" in desc

    def test_no_state_machine(self):
        """State machines are dead. Only chains."""
        planner = make_planner()
        assert not hasattr(planner, 'state_machine')
