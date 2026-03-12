"""Tests for the Bandit CA — SELECT/CONSTRUCT decision layer.

Tests the Bandit CA factory (Chain-based), BanditRuntime, BanditTools.
No state machines. All orchestration is via SDNA EvalChain.
"""

import pytest
from compoctopus.bandit import (
    make_bandit,
    BanditRuntime,
    BanditTools,
    BanditResult,
    BANDIT_STATE_INSTRUCTIONS,
)
from compoctopus.registry import Registry
from compoctopus.types import ArmKind


class TestBanditChainArchitecture:
    """Test the Bandit's Chain-based architecture."""

    def test_has_chain(self):
        registry = Registry()
        bandit = make_bandit(registry)
        assert bandit.chain is not None

    def test_chain_is_eval_chain(self):
        from compoctopus.chain_ontology import EvalChain
        registry = Registry()
        bandit = make_bandit(registry)
        assert isinstance(bandit.chain, EvalChain)

    def test_chain_has_evaluator(self):
        registry = Registry()
        bandit = make_bandit(registry)
        assert bandit.chain.evaluator is not None
        assert bandit.chain.evaluator.name == "construct"

    def test_chain_has_select_link(self):
        registry = Registry()
        bandit = make_bandit(registry)
        assert len(bandit.chain.links) == 1
        assert bandit.chain.links[0].name == "select"

    def test_select_is_sdnac_or_config_link(self):
        """SELECT phase is SDNAC (with SDNA) or ConfigLink (without)."""
        registry = Registry()
        bandit = make_bandit(registry)
        link = bandit.chain.links[0]
        assert hasattr(link, 'execute'), "SELECT link must be executable"
        assert hasattr(link, 'config'), "SELECT link must have config"

    def test_evaluator_is_function_link(self):
        from compoctopus.chain_ontology import FunctionLink
        registry = Registry()
        bandit = make_bandit(registry)
        assert isinstance(bandit.chain.evaluator, FunctionLink)

    def test_describe_shows_chain(self):
        registry = Registry()
        bandit = make_bandit(registry)
        desc = bandit.describe()
        assert "chain=" in desc
        assert "bandit" in desc
        assert "EvalChain" in desc

    def test_no_state_machine(self):
        """State machines are dead. Only chains."""
        registry = Registry()
        bandit = make_bandit(registry)
        assert not hasattr(bandit, 'state_machine')

    def test_max_cycles(self):
        registry = Registry()
        bandit = make_bandit(registry)
        assert bandit.chain.max_cycles == 5


class TestBanditPrompts:
    """Test Bandit prompt content."""

    def test_select_instructions_exist(self):
        assert "SELECT" in BANDIT_STATE_INSTRUCTIONS
        assert len(BANDIT_STATE_INSTRUCTIONS["SELECT"]) > 0

    def test_construct_instructions_exist(self):
        assert "CONSTRUCT" in BANDIT_STATE_INSTRUCTIONS
        assert len(BANDIT_STATE_INSTRUCTIONS["CONSTRUCT"]) > 0

    def test_select_references_tags(self):
        instr = BANDIT_STATE_INSTRUCTIONS["SELECT"]
        assert "<SELECT>" in instr
        assert "CONSTRUCT" in instr


class TestBanditTools:
    """Test BanditTools query methods."""

    def test_query_registry_empty(self):
        import json
        registry = Registry()
        tools = BanditTools(registry, {}, {})
        result = json.loads(tools.query_registry("system_prompt"))
        assert result["kind"] == "system_prompt"
        assert result["arms"] == []

    def test_list_golden_chains_empty(self):
        import json
        tools = BanditTools(Registry(), {}, {})
        result = json.loads(tools.list_golden_chains())
        assert result["golden_chains"] == {}

    def test_list_arm_kinds(self):
        import json
        registry = Registry()
        tools = BanditTools(registry, {}, {})
        result = json.loads(tools.list_arm_kinds())
        assert "arm_kinds" in result


class TestBanditResult:
    """Test the BanditResult dataclass."""

    def test_success_result(self):
        result = BanditResult(
            status="success",
            arm_name="test_arm",
            arm_kind=ArmKind.SYSTEM_PROMPT,
            output={"prompt": "hello"},
            decision="select",
        )
        assert result.status == "success"
        assert result.decision == "select"

    def test_failed_result(self):
        result = BanditResult(
            status="failed",
            arm_kind=ArmKind.SYSTEM_PROMPT,
        )
        assert result.status == "failed"
        assert result.arm_name == ""


class TestBanditRuntime:
    """Test BanditRuntime creation."""

    def test_runtime_creation(self):
        registry = Registry()
        runtime = BanditRuntime(registry)
        assert runtime.rewards == {}
        assert runtime.golden_chains == {}
