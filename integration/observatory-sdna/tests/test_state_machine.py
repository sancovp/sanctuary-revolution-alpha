"""Tests for StateMachine phase management."""

from observatory.state_machine import StateMachine
from observatory.config import PHASES


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine("test")
        assert sm.name == "test"
        assert sm.phase == "observe"
        assert sm.iteration == 0
        assert sm.data == {}
        assert sm.history == []

    def test_phase_sequence(self):
        sm = StateMachine("test")
        expected = ["hypothesize", "proposal", "experiment", "analyze", "observe"]
        for expected_phase in expected:
            actual = sm.next()
            assert actual == expected_phase

    def test_iteration_increments_on_wrap(self):
        sm = StateMachine("test")
        assert sm.iteration == 0

        # Go through full cycle
        for _ in range(len(PHASES)):
            sm.next()

        assert sm.iteration == 1
        assert sm.phase == "observe"

    def test_two_full_cycles(self):
        sm = StateMachine("test")
        for _ in range(len(PHASES) * 2):
            sm.next()
        assert sm.iteration == 2
        assert sm.phase == "observe"

    def test_set_and_get_data(self):
        sm = StateMachine("test")
        sm.set_data("hypothesis", "X causes Y")
        assert sm.get_data("hypothesis") == "X causes Y"
        assert sm.get_data("nonexistent") is None

    def test_data_resets_on_next(self):
        sm = StateMachine("test")
        sm.set_data("key", "value")
        sm.next()
        assert sm.get_data("key") is None

    def test_history_records_phases(self):
        sm = StateMachine("test")
        sm.set_data("obs", "something")
        sm.next()

        assert len(sm.history) == 1
        assert sm.history[0]["phase"] == "observe"
        assert sm.history[0]["iteration"] == 0
        assert sm.history[0]["data"]["obs"] == "something"

    def test_to_dict(self):
        sm = StateMachine("test")
        sm.set_data("k", "v")
        d = sm.to_dict()
        assert d["name"] == "test"
        assert d["phase"] == "observe"
        assert d["iteration"] == 0
        assert d["data"] == {"k": "v"}

    def test_from_dict_roundtrip(self):
        sm = StateMachine("test")
        sm.set_data("key", "val")
        sm.next()
        sm.next()

        d = sm.to_dict()
        sm2 = StateMachine.from_dict(d)

        assert sm2.name == sm.name
        assert sm2.phase == sm.phase
        assert sm2.iteration == sm.iteration
        assert sm2.data == sm.data
        assert sm2.history == sm.history
