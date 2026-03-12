"""
RNG Module Base - Probabilistic event injection system.

The RNG module fires events based on probability, creating emergent
behavior in the PAIA harness.
"""
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable


class EventDomain(Enum):
    PSYCHE = "psyche"   # Internal state (emotions, personality)
    WORLD = "world"     # External events (scheduled, random, other agents)
    SYSTEM = "system"   # Infrastructure (context, MCP health, resources)


@dataclass
class RNGEvent:
    """An event that may fire based on probability."""
    name: str
    domain: EventDomain
    probability: float  # 0.0 to 1.0
    message: str
    priority: int = 5  # 1-10, higher = more important
    cooldown_seconds: int = 0  # Minimum time between fires
    last_fired: float = 0.0
    condition: Optional[Callable[[], bool]] = None  # Optional gate

    def should_fire(self, current_time: float) -> bool:
        """Check if event should fire based on probability and conditions."""
        # Check cooldown
        if current_time - self.last_fired < self.cooldown_seconds:
            return False

        # Check condition gate
        if self.condition and not self.condition():
            return False

        # Roll the dice
        return random.random() < self.probability

    def fire(self, current_time: float) -> str:
        """Fire the event and return the injection message."""
        self.last_fired = current_time
        return self.message


class RNGModule(ABC):
    """Base class for RNG modules."""

    def __init__(self, domain: EventDomain):
        self.domain = domain
        self.events: list[RNGEvent] = []
        self.enabled = True

    @abstractmethod
    def load_events(self) -> None:
        """Load events from config."""
        pass

    def register_event(self, event: RNGEvent) -> None:
        """Register an event to this module."""
        self.events.append(event)

    def tick(self, current_time: float) -> list[str]:
        """Check all events and return any that fire."""
        if not self.enabled:
            return []

        injections = []
        for event in self.events:
            if event.should_fire(current_time):
                injections.append(event.fire(current_time))

        return injections

    def adjust_probability(self, event_name: str, new_prob: float) -> None:
        """Adjust probability of a specific event."""
        for event in self.events:
            if event.name == event_name:
                event.probability = max(0.0, min(1.0, new_prob))
                break
