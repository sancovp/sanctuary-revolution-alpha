"""Harness - The execution layer for sanctuary-revolution.

Runtime control (harness, hooks, events, output watcher, terminal UI,
self-commands) is now provided by cave-harness. Import from cave.core.

Sancrev-specific: PersonaControl, GEAR events.
"""
from .core import (
    PersonaControl,
    PERSONA_FLAG,
)
from .events import (
    GEAREventType,
    GEARDimensionType,
    AcceptanceEvent,
    GEARProofHandler,
    gear_event,
    emit_gear_state,
    emit_dimension_update,
    emit_level_up,
    emit_tier_advanced,
)

__all__ = [
    # Core (sancrev-specific)
    "PersonaControl",
    "PERSONA_FLAG",
    # GEAR Events
    "GEAREventType",
    "GEARDimensionType",
    "AcceptanceEvent",
    "GEARProofHandler",
    "gear_event",
    "emit_gear_state",
    "emit_dimension_update",
    "emit_level_up",
    "emit_tier_advanced",
]
