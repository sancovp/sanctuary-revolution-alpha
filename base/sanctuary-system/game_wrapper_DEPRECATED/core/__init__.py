"""Core game wrapper components."""
from .harness import PAIAHarness, HarnessConfig
from .hook_control import HookControl, HookType, ALL_HOOKS
from .persona_control import PersonaControl, PERSONA_FLAG
from .output_watcher import OutputWatcher, DetectedEvent, EventType
from .event_router import EventRouter, Event, EventSource, EventOutput

__all__ = [
    "PAIAHarness",
    "HarnessConfig",
    "HookControl",
    "HookType",
    "ALL_HOOKS",
    "PersonaControl",
    "PERSONA_FLAG",
    "OutputWatcher",
    "DetectedEvent",
    "EventType",
    "EventRouter",
    "Event",
    "EventSource",
    "EventOutput",
]
