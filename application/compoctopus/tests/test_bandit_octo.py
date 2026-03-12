"""Tests for the Bandit .octo annealed output."""

import pytest
from compoctopus.bandit import (
    Bandit,
    GoldenChain,
    BanditOutcome,
    make_bandit,
)


class TestGoldenChain:
    """Test GoldenChain dataclass."""

    def test_create_golden_chain(self):
        chain = GoldenChain(
            name="test_chain",
            task_pattern=".*test.*",
            config={"key": "value"},
            success_count=5,
            last_used="2024-01-01T00:00:00",
        )
        assert chain.name == "test_chain"
        assert chain.success_count == 5

    def test_default_values(self):
        chain = GoldenChain(name="default", task_pattern="test", config={})
        assert chain.success_count == 0
        assert chain.last_used is None


class TestBanditOutcome:
    """Test BanditOutcome dataclass."""

    def test_create_outcome(self):
        outcome = BanditOutcome(
            task_description="Test task",
            strategy="select",
            config_used={"key": "value"},
            success=True,
            timestamp="2024-01-01T00:00:00",
        )
        assert outcome.task_description == "Test task"
        assert outcome.strategy == "select"
        assert outcome.success is True


class TestBandit:
    """Test Bandit class."""

    def test_make_bandit_creates_instance(self):
        bandit = make_bandit()
        assert isinstance(bandit, Bandit)
        assert bandit.name == "bandit"

    def test_state_machine_is_created(self):
        bandit = make_bandit()
        assert bandit.state_machine is not None

    def test_empty_golden_chains_initially(self):
        bandit = make_bandit()
        assert bandit.golden_chains == {}

    def test_empty_outcomes_initially(self):
        bandit = make_bandit()
        assert bandit.outcomes == []

    def test_lookup_returns_none_for_empty(self):
        bandit = make_bandit()
        result = bandit.lookup("some task description")
        assert result is None

    def test_lookup_finds_matching_chain(self):
        bandit = make_bandit()
        chain = GoldenChain(
            name="test",
            task_pattern="python",
            config={"lang": "python"},
            success_count=3,
        )
        bandit.golden_chains["test"] = chain
        result = bandit.lookup("write some python code")
        assert result is not None
        assert result.name == "test"

    def test_select_increments_success_count(self):
        bandit = make_bandit()
        chain = GoldenChain(
            name="test",
            task_pattern=".*",
            config={"key": "value"},
            success_count=0,
        )
        initial_count = chain.success_count
        result = bandit.select(chain)
        assert chain.success_count == initial_count + 1
        assert result == {"key": "value"}

    def test_construct_returns_default_config(self):
        bandit = make_bandit()
        result = bandit.construct("my task")
        assert result["task_description"] == "my task"
        assert result["strategy"] == "construct"

    def test_record_creates_outcome(self):
        bandit = make_bandit()
        outcome = bandit.record(
            task_description="test task",
            strategy="select",
            config={"key": "value"},
            success=True,
        )
        assert isinstance(outcome, BanditOutcome)
        assert len(bandit.outcomes) == 1
        assert bandit.outcomes[0].success is True

    def test_record_graduates_on_construct_success(self):
        bandit = make_bandit()
        bandit.record(
            task_description="new python task",
            strategy="construct",
            config={"lang": "python"},
            success=True,
        )
        assert len(bandit.golden_chains) == 1

    def test_graduate_creates_golden_chain(self):
        bandit = make_bandit()
        chain = bandit.graduate("python task", {"lang": "python"})
        assert isinstance(chain, GoldenChain)
        assert chain.config == {"lang": "python"}
        assert chain.success_count == 1
        assert len(bandit.golden_chains) == 1
