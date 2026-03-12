"""World RNG Module - External events (scheduled, random, other agents)."""
from utils.rng.base import RNGModule, RNGEvent, EventDomain


class WorldModule(RNGModule):
    """External world events."""

    def __init__(self):
        super().__init__(EventDomain.WORLD)
        self.load_events()

    def load_events(self):
        # Memory resurface
        self.register_event(RNGEvent(
            name="memory_resurface", domain=self.domain, probability=0.08,
            message="[WORLD] A memory from a previous session resurfaces...",
            cooldown_seconds=1200
        ))

        # Pattern detection
        self.register_event(RNGEvent(
            name="pattern_detected", domain=self.domain, probability=0.05,
            message="[WORLD] Strange resonance detected between projects...",
            cooldown_seconds=1800
        ))

        # Dream insight (low prob, high value)
        self.register_event(RNGEvent(
            name="dream_insight", domain=self.domain, probability=0.02,
            message="[WORLD] Dream fragment: a connection forms in the dark...",
            priority=8,
            cooldown_seconds=3600
        ))
