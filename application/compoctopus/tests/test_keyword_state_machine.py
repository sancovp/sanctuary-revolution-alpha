"""Tests for KeywordBasedStateMachine — standalone, no Heaven dependency."""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "heaven_patch"))
from keyword_state_machine import KeywordBasedStateMachine, StateConfig


class TestStateConfig:
    def test_defaults(self):
        cfg = StateConfig()
        assert cfg.goal == ""
        assert cfg.tools == []
        assert cfg.prompt_suffix == ""

    def test_with_values(self):
        cfg = StateConfig(goal="Write code", tools=["write_file"])
        assert cfg.goal == "Write code"


class TestStateMachineInit:
    def test_basic_creation(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(goal="do A"), "B": StateConfig(goal="do B")},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
        )
        assert sm.current_state == "A"
        assert sm.cycles_completed == 0
        assert not sm.is_terminal

    def test_empty_states_raises(self):
        with pytest.raises(ValueError, match="at least one state"):
            KeywordBasedStateMachine(name="bad", states={}, initial_state="A")

    def test_invalid_initial_state(self):
        with pytest.raises(ValueError, match="Initial state"):
            KeywordBasedStateMachine(name="bad", states={"A": StateConfig()}, initial_state="X")

    def test_invalid_terminal_state(self):
        with pytest.raises(ValueError, match="Terminal states"):
            KeywordBasedStateMachine(name="bad", states={"A": StateConfig()},
                                    initial_state="A", terminal_states={"X"})

    def test_invalid_transition_source(self):
        with pytest.raises(ValueError, match="Transition source"):
            KeywordBasedStateMachine(name="bad", states={"A": StateConfig()},
                                    initial_state="A", transitions={"NONEXISTENT": ["A"]})

    def test_invalid_transition_target(self):
        with pytest.raises(ValueError, match="Transition targets"):
            KeywordBasedStateMachine(name="bad",
                                    states={"A": StateConfig(), "B": StateConfig()},
                                    initial_state="A", transitions={"A": ["X"]})

    def test_default_transitions_fully_connected(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig(), "C": StateConfig()},
            initial_state="A", terminal_states={"C"},
        )
        assert "B" in sm.valid_transitions
        assert "C" in sm.valid_transitions

    def test_state_keywords(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"WRITE": StateConfig(), "TEST": StateConfig(), "DONE": StateConfig()},
            initial_state="WRITE",
        )
        assert sm.state_keywords == ["DONE", "TEST", "WRITE"]


class TestTransitions:
    def _coder_sm(self):
        return KeywordBasedStateMachine(
            name="coder",
            states={
                "WRITE": StateConfig(goal="Write code", tools=["write_file"]),
                "ANNEAL": StateConfig(goal="Anneal", tools=["anneal"]),
                "TEST": StateConfig(goal="Run tests", tools=["run_tests"]),
                "REWRITE": StateConfig(goal="Fix code", tools=["write_file"]),
                "DONE": StateConfig(goal="Complete"),
            },
            initial_state="WRITE", terminal_states={"DONE"},
            transitions={
                "WRITE": ["ANNEAL"], "ANNEAL": ["TEST"],
                "TEST": ["DONE", "REWRITE"], "REWRITE": ["ANNEAL"],
            },
        )

    def test_valid_transition(self):
        sm = self._coder_sm()
        cfg = sm.transition("ANNEAL", "writing complete")
        assert sm.current_state == "ANNEAL"
        assert cfg.goal == "Anneal"

    def test_invalid_state(self):
        sm = self._coder_sm()
        with pytest.raises(ValueError, match="does not exist"):
            sm.transition("NONEXISTENT")

    def test_invalid_transition(self):
        sm = self._coder_sm()
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition("TEST")

    def test_terminal_blocks(self):
        sm = self._coder_sm()
        sm.transition("ANNEAL")
        sm.transition("TEST")
        sm.transition("DONE")
        assert sm.is_terminal
        with pytest.raises(ValueError, match="terminal state"):
            sm.transition("WRITE")

    def test_full_happy_path(self):
        sm = self._coder_sm()
        sm.transition("ANNEAL")
        sm.transition("TEST")
        sm.transition("DONE")
        assert sm.is_terminal

    def test_rewrite_loop(self):
        sm = self._coder_sm()
        sm.transition("ANNEAL")
        sm.transition("TEST")
        sm.transition("REWRITE")
        sm.transition("ANNEAL")
        sm.transition("TEST")
        sm.transition("DONE")
        assert sm.is_terminal
        assert len(sm._history) == 6

    def test_valid_transitions_property(self):
        sm = self._coder_sm()
        assert sm.valid_transitions == ["ANNEAL"]
        sm.transition("ANNEAL")
        assert sm.valid_transitions == ["TEST"]


class TestCycleCounter:
    """Test cycles_completed tracking."""

    def test_reset_increments_cycle(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
        )
        assert sm.cycles_completed == 0
        sm.transition("B")
        assert sm.is_terminal
        sm.reset()
        assert sm.cycles_completed == 1
        assert sm.current_state == "A"
        assert not sm.is_terminal

    def test_multiple_cycles(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
        )
        for i in range(5):
            sm.transition("B")
            sm.reset()
        assert sm.cycles_completed == 5
        assert sm.current_state == "A"

    def test_reset_clears_history(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", transitions={"A": ["B"]},
        )
        sm.transition("B")
        assert len(sm._history) == 1
        sm.reset()
        assert sm._history == []


class TestProcessKVs:
    """Test process_kvs — consume/delete/transition pattern."""

    def _sm(self):
        return KeywordBasedStateMachine(
            name="test",
            states={
                "WRITE": StateConfig(goal="Write"), "ANNEAL": StateConfig(goal="Anneal"),
                "TEST": StateConfig(goal="Test"), "DONE": StateConfig(goal="Done"),
            },
            initial_state="WRITE", terminal_states={"DONE"},
            transitions={
                "WRITE": ["ANNEAL"], "ANNEAL": ["TEST"], "TEST": ["DONE", "WRITE"],
            },
        )

    def test_valid_transition_returns_consumed_key(self):
        sm = self._sm()
        consumed = sm.process_kvs({"ANNEAL": "ready to anneal"})
        assert consumed == ["ANNEAL"]
        assert sm.current_state == "ANNEAL"

    def test_caller_can_read_new_config(self):
        sm = self._sm()
        sm.process_kvs({"ANNEAL": "go"})
        # Caller reads sm.config — NOT sm setting agent.goal
        assert sm.config.goal == "Anneal"

    def test_ignores_current_state(self):
        sm = self._sm()
        consumed = sm.process_kvs({"WRITE": "still writing"})
        assert consumed == []
        assert sm.current_state == "WRITE"

    def test_ignores_invalid_transition(self):
        sm = self._sm()
        consumed = sm.process_kvs({"DONE": "nope"})
        assert consumed == []
        assert sm.current_state == "WRITE"

    def test_empty_returns_empty(self):
        sm = self._sm()
        assert sm.process_kvs({}) == []
        assert sm.process_kvs(None) == []

    def test_multiple_states_prefers_valid(self):
        sm = self._sm()
        consumed = sm.process_kvs({
            "TEST": "not valid from WRITE",
            "ANNEAL": "this one is valid",
        })
        assert consumed == ["ANNEAL"]
        assert sm.current_state == "ANNEAL"

    def test_handles_list_values(self):
        sm = self._sm()
        consumed = sm.process_kvs({"ANNEAL": ["first", "second"]})
        assert consumed == ["ANNEAL"]
        assert sm.current_state == "ANNEAL"

    def test_only_one_transition_per_call(self):
        """Even if multiple valid targets, only one fires."""
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig(), "C": StateConfig()},
            initial_state="A", transitions={"A": ["B", "C"]},
        )
        consumed = sm.process_kvs({"B": "go B", "C": "go C"})
        assert len(consumed) == 1
        assert sm.current_state in ("B", "C")

    def test_non_state_keys_not_consumed(self):
        sm = self._sm()
        extracted = {"ANNEAL": "go", "SUMMARY": "some summary", "other_kw": "data"}
        consumed = sm.process_kvs(extracted)
        assert consumed == ["ANNEAL"]
        # Other keys still in the dict — caller deletes consumed ones
        assert "SUMMARY" in extracted
        assert "other_kw" in extracted

    def test_after_transition_new_valid_targets(self):
        sm = self._sm()
        sm.process_kvs({"ANNEAL": "go"})
        consumed = sm.process_kvs({"TEST": "test now"})
        assert consumed == ["TEST"]
        assert sm.current_state == "TEST"

    def test_terminal_reachable(self):
        sm = self._sm()
        sm.process_kvs({"ANNEAL": "go"})
        sm.process_kvs({"TEST": "go"})
        consumed = sm.process_kvs({"DONE": "all done"})
        assert consumed == ["DONE"]
        assert sm.is_terminal


class TestKWInstructions:
    def test_includes_cycle_count(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(goal="do A"), "B": StateConfig(goal="do B")},
            initial_state="A", transitions={"A": ["B"]},
        )
        instructions = sm.build_kw_instructions()
        assert "Cycles completed: 0" in instructions

    def test_cycle_count_updates(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
        )
        sm.transition("B")
        sm.reset()
        instructions = sm.build_kw_instructions()
        assert "Cycles completed: 1" in instructions

    def test_build_transition_prompt(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(goal="go"), "B": StateConfig()},
            initial_state="A", transitions={"A": ["B"]},
        )
        prompt = sm.build_transition_prompt()
        assert "<STATE_MACHINE>" in prompt
        assert "</STATE_MACHINE>" in prompt


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", transitions={"A": ["B"]},
            heaven_data_dir=str(tmp_path),
        )
        sm.transition("B")
        sm.save_state("my_agent")

        sm2 = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", transitions={"A": ["B"]},
            heaven_data_dir=str(tmp_path),
        )
        assert sm2.load_state("my_agent")
        assert sm2.current_state == "B"

    def test_persists_cycle_count(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
            heaven_data_dir=str(tmp_path),
        )
        sm.transition("B")
        sm.reset()  # cycles_completed = 1
        sm.transition("B")
        sm.save_state("my_agent")

        sm2 = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
            heaven_data_dir=str(tmp_path),
        )
        sm2.load_state("my_agent")
        assert sm2.cycles_completed == 1
        assert sm2.current_state == "B"

    def test_unnamed_agent_raises(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="test", states={"A": StateConfig()}, initial_state="A",
            heaven_data_dir=str(tmp_path),
        )
        with pytest.raises(ValueError, match="unnamed agent"):
            sm.save_state("default")
        with pytest.raises(ValueError, match="unnamed agent"):
            sm.save_state("")
        with pytest.raises(ValueError, match="unnamed agent"):
            sm.save_state(None)

    def test_load_no_saved_state(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="test", states={"A": StateConfig()}, initial_state="A",
            heaven_data_dir=str(tmp_path),
        )
        assert not sm.load_state("nonexistent")

    def test_clear_state(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", transitions={"A": ["B"]},
            heaven_data_dir=str(tmp_path),
        )
        sm.transition("B")
        sm.save_state("my_agent")
        sm.clear_state("my_agent")
        assert not sm.load_state("my_agent")


class TestSerialization:
    def test_roundtrip(self):
        sm = KeywordBasedStateMachine(
            name="coder",
            states={
                "WRITE": StateConfig(goal="Write", tools=["w"]),
                "TEST": StateConfig(goal="Test", tools=["t"]),
                "DONE": StateConfig(goal="Done"),
            },
            initial_state="WRITE", terminal_states={"DONE"},
            transitions={"WRITE": ["TEST"], "TEST": ["WRITE", "DONE"]},
        )
        sm.transition("TEST", "wrote it")

        data = sm.to_dict()
        sm2 = KeywordBasedStateMachine.from_dict(data)
        assert sm2.current_state == "TEST"
        assert sm2.cycles_completed == 0

    def test_roundtrip_with_cycles(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(), "B": StateConfig()},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
        )
        sm.transition("B")
        sm.reset()
        data = sm.to_dict()
        sm2 = KeywordBasedStateMachine.from_dict(data)
        assert sm2.cycles_completed == 1

    def test_json_serializable(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(goal="go"), "B": StateConfig()},
            initial_state="A", transitions={"A": ["B"]},
        )
        json_str = json.dumps(sm.to_dict())
        assert '"name": "test"' in json_str


class TestMermaid:
    def test_mermaid(self):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"WRITE": StateConfig(), "TEST": StateConfig(), "DONE": StateConfig()},
            initial_state="WRITE", terminal_states={"DONE"},
            transitions={"WRITE": ["TEST"], "TEST": ["WRITE", "DONE"]},
        )
        mermaid = sm.to_mermaid()
        assert "stateDiagram-v2" in mermaid
        assert "[*] --> WRITE" in mermaid
        assert "DONE --> [*]" in mermaid


class TestJSONFile:
    """Test JSON file loading and saving."""

    def test_from_json_file(self):
        """Load the example coder_sm.json config."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "heaven_patch", "examples", "coder_sm.json"
        )
        sm = KeywordBasedStateMachine.from_json_file(config_path)
        assert sm.name == "coder"
        assert sm.initial_state == "WRITE"
        assert sm.current_state == "WRITE"
        assert sm.terminal_states == {"DONE"}
        assert "ANNEAL" in sm.states
        assert sm.states["WRITE"].tools == ["write_file", "read_file"]
        assert sm.valid_transitions == ["ANNEAL"]  # From WRITE, only ANNEAL

    def test_to_json_file(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="test",
            states={"A": StateConfig(goal="go"), "B": StateConfig(goal="stop")},
            initial_state="A", terminal_states={"B"}, transitions={"A": ["B"]},
        )
        sm.transition("B")
        out = str(tmp_path / "sm.json")
        sm.to_json_file(out)

        sm2 = KeywordBasedStateMachine.from_json_file(out)
        assert sm2.name == "test"
        assert sm2.current_state == "B"
        assert sm2.is_terminal

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="SM config not found"):
            KeywordBasedStateMachine.from_json_file("/nonexistent/path.json")

    def test_roundtrip_preserves_all_fields(self, tmp_path):
        sm = KeywordBasedStateMachine(
            name="roundtrip",
            states={
                "X": StateConfig(goal="do X", tools=["t1"], prompt_suffix="px"),
                "Y": StateConfig(goal="do Y", metadata={"key": "val"}),
            },
            initial_state="X", terminal_states={"Y"}, transitions={"X": ["Y"]},
        )
        sm.transition("Y", "done with X")
        sm.reset()  # cycles_completed = 1

        out = str(tmp_path / "rt.json")
        sm.to_json_file(out)
        sm2 = KeywordBasedStateMachine.from_json_file(out)

        assert sm2.name == "roundtrip"
        assert sm2.cycles_completed == 1
        assert sm2.states["X"].tools == ["t1"]
        assert sm2.states["X"].prompt_suffix == "px"
        assert sm2.states["Y"].metadata == {"key": "val"}

