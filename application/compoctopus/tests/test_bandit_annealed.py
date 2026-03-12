"""Tests for the annealed bandit.octo output.

Tests the Bandit class methods based on the spec in bandit_spec.md.
This tests the annealed Python output from bandit.octo.
"""

import pytest
import sys
import os

# Add compoctopus to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'compoctopus'))

from compoctopus.bandit import (
    Bandit,
    GoldenChain,
    BanditOutcome,
    make_bandit,
)


class TestBanditInitialization:
    """Test Bandit initialization."""

    def test_make_bandit_returns_bandit_instance(self):
        """Factory function should return a Bandit instance."""
        bandit = make_bandit()
        assert isinstance(bandit, Bandit)

    def test_bandit_initializes_empty_golden_chains(self):
        """Bandit should start with empty golden_chains dict."""
        bandit = make_bandit()
        assert bandit.golden_chains == {}
        assert isinstance(bandit.golden_chains, dict)

    def test_bandit_initializes_empty_outcomes(self):
        """Bandit should start with empty outcomes list."""
        bandit = make_bandit()
        assert bandit.outcomes == []
        assert isinstance(bandit.outcomes, list)

    def test_bandit_has_name(self):
        """Bandit should have a name attribute."""
        bandit = make_bandit()
        assert bandit.name == "bandit"

    def test_bandit_has_state_machine(self):
        """Bandit should have a state_machine attribute."""
        bandit = make_bandit()
        assert bandit.state_machine is not None


class TestLookup:
    """Test the lookup method."""

    def test_lookup_returns_none_when_empty(self):
        """Lookup should return None when no golden chains exist."""
        bandit = make_bandit()
        result = bandit.lookup("any task description")
        assert result is None

    def test_lookup_finds_matching_pattern(self):
        """Lookup should find a chain where task_pattern matches task_description."""
        bandit = make_bandit()
        chain = GoldenChain(
            name="test_chain",
            task_pattern="write.*file",
            config={"tool": "write_file"},
            success_count=1,
        )
        bandit.golden_chains["test_chain"] = chain
        
        result = bandit.lookup("write a new file")
        assert result is not None
        assert result.name == "test_chain"

    def test_lookup_returns_none_when_no_match(self):
        """Lookup should return None when no pattern matches."""
        bandit = make_bandit()
        chain = GoldenChain(
            name="test_chain",
            task_pattern="read.*file",
            config={"tool": "read_file"},
            success_count=1,
        )
        bandit.golden_chains["test_chain"] = chain
        
        result = bandit.lookup("write a new file")
        assert result is None

    def test_lookup_returns_best_match_by_success_count(self):
        """When multiple chains match, return the one with highest success_count."""
        bandit = make_bandit()
        chain1 = GoldenChain(
            name="chain1",
            task_pattern=".*",  # matches anything
            config={"tool": "tool1"},
            success_count=5,
        )
        chain2 = GoldenChain(
            name="chain2",
            task_pattern=".*",  # matches anything
            config={"tool": "tool2"},
            success_count=10,
        )
        bandit.golden_chains["chain1"] = chain1
        bandit.golden_chains["chain2"] = chain2
        
        result = bandit.lookup("any task")
        assert result is not None
        assert result.success_count == 10
        assert result.name == "chain2"


class TestSelect:
    """Test the select method."""

    def test_select_returns_chain_config(self):
        """Select should return the chain's config."""
        bandit = make_bandit()
        chain = GoldenChain(
            name="test_chain",
            task_pattern="test",
            config={"tool": "write_file", "path": "/tmp/test"},
            success_count=0,
        )
        
        result = bandit.select(chain)
        
        assert result == {"tool": "write_file", "path": "/tmp/test"}

    def test_select_increments_success_count(self):
        """Select should increment the chain's success_count."""
        bandit = make_bandit()
        chain = GoldenChain(
            name="test_chain",
            task_pattern="test",
            config={"tool": "write_file"},
            success_count=3,
        )
        
        bandit.select(chain)
        
        assert chain.success_count == 4

    def test_select_updates_last_used_timestamp(self):
        """Select should update the chain's last_used timestamp."""
        bandit = make_bandit()
        chain = GoldenChain(
            name="test_chain",
            task_pattern="test",
            config={"tool": "write_file"},
            success_count=0,
            last_used=None,
        )
        
        bandit.select(chain)
        
        assert chain.last_used is not None
        assert isinstance(chain.last_used, str)


class TestConstruct:
    """Test the construct method."""

    def test_construct_returns_config_with_task_description(self):
        """Construct should return a config with the task_description."""
        bandit = make_bandit()
        
        result = bandit.construct("write a new Python file")
        
        assert result["task_description"] == "write a new Python file"
        assert result["strategy"] == "construct"

    def test_construct_returns_dict(self):
        """Construct should return a dict."""
        bandit = make_bandit()
        
        result = bandit.construct("any task")
        
        assert isinstance(result, dict)


class TestRecord:
    """Test the record method."""

    def test_record_returns_bandit_outcome(self):
        """Record should return a BanditOutcome."""
        bandit = make_bandit()
        
        result = bandit.record(
            task_description="test task",
            strategy="select",
            config={"tool": "test"},
            success=True,
        )
        
        assert isinstance(result, BanditOutcome)
        assert result.task_description == "test task"
        assert result.strategy == "select"
        assert result.success is True

    def test_record_appends_to_outcomes(self):
        """Record should append the outcome to the outcomes list."""
        bandit = make_bandit()
        
        bandit.record(
            task_description="task 1",
            strategy="construct",
            config={"tool": "test"},
            success=True,
        )
        
        assert len(bandit.outcomes) == 1

    def test_record_multiple_outcomes(self):
        """Multiple records should all be appended."""
        bandit = make_bandit()
        
        bandit.record("task 1", "select", {}, True)
        bandit.record("task 2", "construct", {}, False)
        bandit.record("task 3", "select", {}, True)
        
        assert len(bandit.outcomes) == 3

    def test_record_success_with_construct_graduates(self):
        """Successful construct strategy should trigger graduation."""
        bandit = make_bandit()
        
        bandit.record(
            task_description="write Python test file",
            strategy="construct",
            config={"tool": "write_file"},
            success=True,
        )
        
        # Should have graduated to a golden chain
        assert len(bandit.golden_chains) == 1

    def test_record_failed_construct_does_not_graduate(self):
        """Failed construct strategy should not trigger graduation."""
        bandit = make_bandit()
        
        bandit.record(
            task_description="write Python test file",
            strategy="construct",
            config={"tool": "write_file"},
            success=False,
        )
        
        assert len(bandit.golden_chains) == 0

    def test_record_select_does_not_graduate(self):
        """Select strategy should not trigger graduation (even if successful)."""
        bandit = make_bandit()
        
        # First add a golden chain
        chain = GoldenChain(
            name="existing",
            task_pattern=".*",
            config={},
        )
        bandit.golden_chains["existing"] = chain
        
        bandit.record(
            task_description="any task",
            strategy="select",
            config={},
            success=True,
        )
        
        # Should still only have the original chain
        assert len(bandit.golden_chains) == 1


class TestGraduate:
    """Test the graduate method."""

    def test_graduate_returns_golden_chain(self):
        """Graduate should return a GoldenChain."""
        bandit = make_bandit()
        
        result = bandit.graduate("write test file", {"tool": "write_file"})
        
        assert isinstance(result, GoldenChain)

    def test_graduate_adds_to_golden_chains(self):
        """Graduate should add the new chain to golden_chains dict."""
        bandit = make_bandit()
        
        bandit.graduate("write test file", {"tool": "write_file"})
        
        assert len(bandit.golden_chains) == 1

    def test_graduate_derives_pattern_from_description(self):
        """Graduate should derive task_pattern from description keywords."""
        bandit = make_bandit()
        
        chain = bandit.graduate("write Python test file", {})
        
        # Should use first two words > 2 chars: "write" and "Python"
        assert "write" in chain.task_pattern
        assert "Python" in chain.task_pattern

    def test_graduate_handles_short_description(self):
        """Graduate should handle descriptions with short words."""
        bandit = make_bandit()
        
        chain = bandit.graduate("a b test c", {})
        
        # Should use "test" (only word > 2 chars)
        assert "test" in chain.task_pattern

    def test_graduate_sets_success_count_to_one(self):
        """Newly graduated chain should have success_count of 1."""
        bandit = make_bandit()
        
        chain = bandit.graduate("test task", {})
        
        assert chain.success_count == 1

    def test_graduate_sets_last_used_timestamp(self):
        """Newly graduated chain should have last_used timestamp."""
        bandit = make_bandit()
        
        chain = bandit.graduate("test task", {})
        
        assert chain.last_used is not None
        assert isinstance(chain.last_used, str)


class TestTransition:
    """Test the transition method."""

    def test_transition_validates_current_state(self):
        """Transition should check current state validity."""
        bandit = make_bandit()
        
        # Initial state is LOOKUP, valid transitions are SELECT or CONSTRUCT
        # Trying to transition to DONE should fail
        with pytest.raises(ValueError) as exc_info:
            bandit.transition("DONE")
        
        assert "Invalid transition" in str(exc_info.value)

    def test_transition_to_valid_state(self):
        """Transition to a valid state should work."""
        bandit = make_bandit()
        
        # Initial state is LOOKUP, can transition to SELECT
        bandit.transition("SELECT")
        
        assert bandit.state_machine.current_state == "SELECT"

    def test_transition_sequence(self):
        """Test a full valid transition sequence."""
        bandit = make_bandit()
        
        # LOOKUP -> SELECT -> RECORD -> DONE
        assert bandit.state_machine.current_state == "LOOKUP"
        
        bandit.transition("SELECT")
        assert bandit.state_machine.current_state == "SELECT"
        
        bandit.transition("RECORD")
        assert bandit.state_machine.current_state == "RECORD"
        
        bandit.transition("DONE")
        assert bandit.state_machine.current_state == "DONE"


class TestDataclasses:
    """Test the GoldenChain and BanditOutcome dataclasses."""

    def test_golden_chain_defaults(self):
        """GoldenChain should have default values."""
        chain = GoldenChain(
            name="test",
            task_pattern=".*",
            config={},
        )
        
        assert chain.success_count == 0
        assert chain.last_used is None

    def test_bandit_outcome_fields(self):
        """BanditOutcome should have all required fields."""
        outcome = BanditOutcome(
            task_description="test",
            strategy="select",
            config_used={"tool": "test"},
            success=True,
            timestamp="2024-01-01T00:00:00",
        )
        
        assert outcome.task_description == "test"
        assert outcome.strategy == "select"
        assert outcome.success is True
        assert outcome.timestamp == "2024-01-01T00:00:00"
