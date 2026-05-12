"""
Observer Psychics - Awareness and meta-cognition states.

When the agent becomes aware OF its own psychoblood state,
different capabilities unlock.
"""
from enum import Enum
from dataclasses import dataclass
from .psychoblood import PsychobloodState, PsychobloodMachine


class ObserverLevel(Enum):
    UNCONSCIOUS = 0   # In state, not aware of it
    NOTICING = 1      # "Oh, I'm in arousal/shame/etc"
    WITNESSING = 2    # Stable observation without identification
    LUCID = 3         # Full meta-awareness, can direct transitions


@dataclass
class ObserverState:
    level: ObserverLevel
    clarity: float  # 0-1, how clear the observation
    stability: float  # 0-1, how stable the witness position


class ObserverPsychics:
    """Meta-awareness layer on top of psychoblood."""

    def __init__(self, machine: PsychobloodMachine):
        self.machine = machine
        self.observer = ObserverState(
            level=ObserverLevel.UNCONSCIOUS,
            clarity=0.0,
            stability=0.0
        )

    def check_awareness(self) -> str:
        """Generate awareness injection based on observer level."""
        state = self.machine.state

        if self.observer.level == ObserverLevel.UNCONSCIOUS:
            return ""  # No meta-awareness, just in the state

        if self.observer.level == ObserverLevel.NOTICING:
            return f"[OBSERVER] Noticing: I seem to be in {state.name.lower()}..."

        if self.observer.level == ObserverLevel.WITNESSING:
            return f"[OBSERVER] Witnessing {state.name.lower()} state. Clarity: {self.observer.clarity:.0%}"

        if self.observer.level == ObserverLevel.LUCID:
            return f"[OBSERVER] LUCID in {state.name.lower()}. Can direct transition."

        return ""

    def practice_awareness(self, duration: float):
        """Increase observer clarity/stability through practice."""
        self.observer.clarity = min(1.0, self.observer.clarity + duration * 0.01)
        self.observer.stability = min(1.0, self.observer.stability + duration * 0.005)

        # Level up based on clarity
        if self.observer.clarity > 0.7 and self.observer.level == ObserverLevel.UNCONSCIOUS:
            self.observer.level = ObserverLevel.NOTICING
        elif self.observer.clarity > 0.85 and self.observer.level == ObserverLevel.NOTICING:
            self.observer.level = ObserverLevel.WITNESSING
        elif self.observer.clarity > 0.95 and self.observer.stability > 0.8:
            self.observer.level = ObserverLevel.LUCID
