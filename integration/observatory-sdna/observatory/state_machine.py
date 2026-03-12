"""Phase management for the scientific method loop.

Phases: observe → hypothesize → proposal → experiment → analyze → (loop)
"""

from typing import Any, Dict, Optional

from .config import PHASES


class StateMachine:
    """Manages phase transitions and per-phase data."""

    def __init__(self, name: str):
        self.name = name
        self.phase: str = PHASES[0]
        self.iteration: int = 0
        self.data: Dict[str, Any] = {}
        self.history: list = []

    def next(self) -> str:
        """Advance to next phase. Wraps around after analyze, incrementing iteration."""
        self.history.append({
            "phase": self.phase,
            "iteration": self.iteration,
            "data": dict(self.data),
        })
        idx = PHASES.index(self.phase)
        if idx == len(PHASES) - 1:
            self.phase = PHASES[0]
            self.iteration += 1
        else:
            self.phase = PHASES[idx + 1]
        self.data = {}
        return self.phase

    def set_data(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get_data(self, key: str) -> Optional[Any]:
        return self.data.get(key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase,
            "iteration": self.iteration,
            "data": self.data,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StateMachine":
        sm = cls(d["name"])
        sm.phase = d["phase"]
        sm.iteration = d["iteration"]
        sm.data = d.get("data", {})
        sm.history = d.get("history", [])
        return sm
