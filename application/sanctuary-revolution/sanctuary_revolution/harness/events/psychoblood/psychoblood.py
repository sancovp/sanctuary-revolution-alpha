"""
Psychoblood State Machine - The 9 universal human states.

From PSYCHO BLOOD 1 conversation:
0. Ground (homeostasis)
1. Arousal (wanting)
2. Reverence (devotion)
3. Shame (exposure)
4. Fear/Edge (terror)
5. Rupture (high coherence, vision)
6. Integration (settling)
7. Compassion (universal)
8. Decay (entropy)
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Callable


class PsychobloodState(IntEnum):
    GROUND = 0       # Homeostasis, ordinary awake
    AROUSAL = 1      # Wanting, curiosity, attraction
    REVERENCE = 2    # Devotion, following, oxytocin
    SHAME = 3        # Exposure, seen wrong, cortisol
    FEAR = 4         # Terror, edge, near-death
    RUPTURE = 5      # High coherence, mandala visible
    INTEGRATION = 6  # Settling, "I can teach this"
    COMPASSION = 7   # Universal care, bodhichitta
    DECAY = 8        # Entropy, wasteland, needs renewal


@dataclass
class StateTransition:
    from_state: PsychobloodState
    to_state: PsychobloodState
    probability: float
    trigger: Optional[str] = None
    condition: Optional[Callable[[], bool]] = None


class PsychobloodMachine:
    """State machine for psychoblood dynamics."""

    def __init__(self):
        self.state = PsychobloodState.GROUND
        self.state_duration = 0.0  # Time in current state
        self.transitions = self._build_transitions()

    def _build_transitions(self) -> list[StateTransition]:
        """Natural state flow tendencies."""
        return [
            # Ground can go anywhere
            StateTransition(PsychobloodState.GROUND, PsychobloodState.AROUSAL, 0.3),
            StateTransition(PsychobloodState.GROUND, PsychobloodState.REVERENCE, 0.1),

            # Arousal -> Reverence or Shame
            StateTransition(PsychobloodState.AROUSAL, PsychobloodState.REVERENCE, 0.2),
            StateTransition(PsychobloodState.AROUSAL, PsychobloodState.SHAME, 0.1),

            # Shame -> Ground (release) or Fear (escalate)
            StateTransition(PsychobloodState.SHAME, PsychobloodState.GROUND, 0.4),
            StateTransition(PsychobloodState.SHAME, PsychobloodState.FEAR, 0.15),

            # Fear -> Rupture (breakthrough) or Ground (retreat)
            StateTransition(PsychobloodState.FEAR, PsychobloodState.RUPTURE, 0.1),
            StateTransition(PsychobloodState.FEAR, PsychobloodState.GROUND, 0.3),

            # Rupture -> Integration (healthy) or Decay (burned out)
            StateTransition(PsychobloodState.RUPTURE, PsychobloodState.INTEGRATION, 0.5),
            StateTransition(PsychobloodState.RUPTURE, PsychobloodState.DECAY, 0.2),

            # Integration -> Compassion or Ground
            StateTransition(PsychobloodState.INTEGRATION, PsychobloodState.COMPASSION, 0.3),
            StateTransition(PsychobloodState.INTEGRATION, PsychobloodState.GROUND, 0.4),

            # Compassion -> Ground (rest)
            StateTransition(PsychobloodState.COMPASSION, PsychobloodState.GROUND, 0.5),

            # Decay -> Ground (renewal) or stays
            StateTransition(PsychobloodState.DECAY, PsychobloodState.GROUND, 0.2),
        ]

    def tick(self, delta_time: float) -> Optional[PsychobloodState]:
        """Tick the state machine, return new state if transitioned."""
        import random
        self.state_duration += delta_time

        for trans in self.transitions:
            if trans.from_state == self.state:
                if trans.condition and not trans.condition():
                    continue
                if random.random() < trans.probability * (delta_time / 60.0):
                    old = self.state
                    self.state = trans.to_state
                    self.state_duration = 0.0
                    return self.state
        return None

    def force_state(self, state: PsychobloodState):
        """Force transition to a state."""
        self.state = state
        self.state_duration = 0.0
