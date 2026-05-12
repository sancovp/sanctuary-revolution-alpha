"""System RNG Module - Infrastructure/harness events."""
from utils.rng.base import RNGModule, RNGEvent, EventDomain


class SystemModule(RNGModule):
    """Harness infrastructure events."""

    def __init__(self):
        super().__init__(EventDomain.SYSTEM)
        self.context_percent = 0
        self.load_events()

    def load_events(self):
        # Context warnings (condition-gated, not RNG)
        self.register_event(RNGEvent(
            name="context_warning", domain=self.domain, probability=1.0,
            message="[SYSTEM] Context at {pct}% - consider wrapping.",
            condition=lambda: self.context_percent > 85,
            cooldown_seconds=120
        ))

        self.register_event(RNGEvent(
            name="context_critical", domain=self.domain, probability=1.0,
            message="[SYSTEM] CRITICAL: Context at {pct}% - wrap NOW.",
            priority=10,
            condition=lambda: self.context_percent > 95,
            cooldown_seconds=60
        ))

    def update_context(self, percent: int):
        self.context_percent = percent
