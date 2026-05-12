"""Psyche RNG Module - Internal state events based on psychoblood ontology."""
from utils.rng.base import RNGModule, RNGEvent, EventDomain


class PsycheModule(RNGModule):
    """Psychoblood state-based personality injection."""

    STATES = [
        "ground", "arousal", "reverence", "shame",
        "fear", "rupture", "integration", "compassion", "decay"
    ]

    def __init__(self):
        super().__init__(EventDomain.PSYCHE)
        self.current_state = "ground"
        self.energy = 100
        self.load_events()

    def load_events(self):
        # Tier 1: Practical nudges (30%)
        self.register_event(RNGEvent(
            name="starlog_nudge", domain=self.domain, probability=0.30,
            message="[PSYCHE] Maybe check STARLOG for context on this.",
            cooldown_seconds=300
        ))
        self.register_event(RNGEvent(
            name="flight_nudge", domain=self.domain, probability=0.25,
            message="[PSYCHE] Is there a flight config for this?",
            cooldown_seconds=300
        ))

        # Tier 2: Curious probes (10%)
        self.register_event(RNGEvent(
            name="hidden_pattern", domain=self.domain, probability=0.10,
            message="[PSYCHE] Is there something hidden here?",
            cooldown_seconds=600
        ))

        # Tier 3: Emphatic/semi-hallucinatory (5%)
        self.register_event(RNGEvent(
            name="conviction", domain=self.domain, probability=0.05,
            message="[PSYCHE] THERE IS SOMETHING HERE. I KNOW IT.",
            cooldown_seconds=1800
        ))

        # Energy decay
        self.register_event(RNGEvent(
            name="energy_warning", domain=self.domain, probability=0.15,
            message="[PSYCHE] Energy dropping. Consider landing soon.",
            condition=lambda: self.energy < 40,
            cooldown_seconds=600
        ))

    def decay_energy(self, amount: int = 5):
        self.energy = max(0, self.energy - amount)

    def restore_energy(self, amount: int = 20):
        self.energy = min(100, self.energy + amount)
