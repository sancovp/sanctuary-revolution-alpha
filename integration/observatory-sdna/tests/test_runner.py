"""Tests for Runner orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass, field
from typing import Dict, Any

from observatory.runner import Runner
from observatory.state_machine import StateMachine
from observatory.connector import SDNACConnector


@dataclass
class MockResult:
    status: MagicMock = field(default_factory=lambda: MagicMock(value="success"))
    context: Dict[str, Any] = field(default_factory=dict)
    error: str = None


def make_runner(researcher_context=None, connector_result=None):
    """Build a Runner with mocked components."""
    if researcher_context is None:
        researcher_context = {"text": "researcher output"}

    mock_researcher = MagicMock()
    mock_researcher.execute = AsyncMock(return_value=MockResult(context=researcher_context))

    mock_connector = MagicMock(spec=SDNACConnector)
    mock_connector.send_and_wait = AsyncMock(return_value=connector_result or {"text": "grug done"})

    state = StateMachine("test")
    runner = Runner(mock_connector, mock_researcher, state)
    return runner, mock_researcher, mock_connector


class TestRunOneStep:
    @pytest.mark.asyncio
    async def test_advances_phase(self):
        runner, _, _ = make_runner()
        result = await runner.run_one_step()

        assert result["completed_phase"] == "observe"
        assert result["next_phase"] == "hypothesize"
        assert runner.state.phase == "hypothesize"

    @pytest.mark.asyncio
    async def test_calls_researcher(self):
        runner, researcher, _ = make_runner()
        await runner.run_one_step()

        researcher.execute.assert_called_once()
        ctx = researcher.execute.call_args[0][0]
        assert ctx["phase"] == "observe"
        assert ctx["iteration"] == 0

    @pytest.mark.asyncio
    async def test_calls_connector_in_experiment_phase(self):
        runner, researcher, connector = make_runner(
            researcher_context={"needs_grug": True, "experiment_spec": "run tests"}
        )
        # Advance to experiment phase
        runner.state.phase = "experiment"

        # First call returns needs_grug, second call is analysis
        researcher.execute = AsyncMock(
            side_effect=[
                MockResult(context={"needs_grug": True, "experiment_spec": "run tests"}),
                MockResult(context={"text": "analysis done"}),
            ]
        )

        result = await runner.run_one_step()

        connector.send_and_wait.assert_called_once_with("run tests", {"needs_grug": True, "experiment_spec": "run tests"})
        assert researcher.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_no_connector_call_outside_experiment(self):
        runner, _, connector = make_runner()
        # observe phase — should NOT call connector
        await runner.run_one_step()
        connector.send_and_wait.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_connector_without_needs_grug(self):
        runner, _, connector = make_runner(researcher_context={"text": "no grug needed"})
        runner.state.phase = "experiment"
        await runner.run_one_step()
        connector.send_and_wait.assert_not_called()

    @pytest.mark.asyncio
    async def test_stores_phase_data(self):
        runner, _, _ = make_runner(
            researcher_context={"text": "ok", "phase_data": {"finding": "X"}}
        )
        await runner.run_one_step()
        # Data was stored before advancing, now in history
        assert runner.state.history[0]["data"]["finding"] == "X"


class TestRunWithProposalGate:
    @pytest.mark.asyncio
    async def test_runs_until_proposal(self):
        runner, researcher, _ = make_runner()
        researcher.execute = AsyncMock(return_value=MockResult(context={"text": "ok"}))

        result = await runner.run_with_proposal_gate()

        assert result["phase"] == "proposal"
        assert result["awaiting_approval"] is True

    @pytest.mark.asyncio
    async def test_accept_at_proposal(self):
        runner, _, _ = make_runner()
        runner.state.phase = "proposal"

        result = await runner.run_with_proposal_gate(hint="accept")

        assert result["completed_phase"] == "proposal"
        assert result["next_phase"] == "experiment"

    @pytest.mark.asyncio
    async def test_quit_resets_to_observe(self):
        runner, _, _ = make_runner()
        runner.state.phase = "proposal"

        result = await runner.run_with_proposal_gate(hint="quit")

        assert result["phase"] == "observe"
        assert result["status"] == "quit"


class TestRunAutonomous:
    @pytest.mark.asyncio
    async def test_completes_one_cycle(self):
        runner, _, _ = make_runner()
        result = await runner.run_autonomous(max_cycles=1)

        assert result["status"] == "cycles_complete"
        assert result["iterations_completed"] == 1
        assert runner.state.iteration == 1


class TestNeedsGrug:
    def test_true_in_experiment_with_flag(self):
        runner, _, _ = make_runner()
        runner.state.phase = "experiment"
        result = MockResult(context={"needs_grug": True})
        assert runner._needs_grug(result) is True

    def test_false_outside_experiment(self):
        runner, _, _ = make_runner()
        runner.state.phase = "observe"
        result = MockResult(context={"needs_grug": True})
        assert runner._needs_grug(result) is False

    def test_false_without_flag(self):
        runner, _, _ = make_runner()
        runner.state.phase = "experiment"
        result = MockResult(context={})
        assert runner._needs_grug(result) is False
