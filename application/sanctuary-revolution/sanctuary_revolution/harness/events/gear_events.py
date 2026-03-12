"""
GEAR Events - Bidirectional bus between GEAR and Frontend.

Outbound: GEAR changes → emit event → SSE → frontend displays
Inbound: User accepts/rejects in UI → event → updates GEAR proof

The frontend is where user provides PROOF:
- "I accept this component" → G proof (gear exists)
- "This is published" → A proof (achievement validated)
- "This actually changed something" → R proof (reality grounded)
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime

from cave.core.event_router import (
    Event, EventSource, EventOutput,
    HookInjection, InjectionType,
    InTerminalObject, TerminalObjectType
)

logger = logging.getLogger(__name__)


# =============================================================================
# GEAR EVENT TYPES
# =============================================================================

class GEAREventType(str, Enum):
    """Types of GEAR events."""
    # Outbound (GEAR → Frontend)
    GEAR_STATE_CHANGED = "gear_state_changed"  # Full state update
    DIMENSION_UPDATED = "dimension_updated"    # Single dimension changed
    LEVEL_UP = "level_up"                      # Level increased
    TIER_ADVANCED = "tier_advanced"            # Component tier advanced
    GOLDEN_CHANGED = "golden_changed"          # Component goldenization changed

    # Inbound (Frontend → GEAR)
    COMPONENT_ACCEPTED = "component_accepted"   # User accepted a component (G proof)
    ACHIEVEMENT_VALIDATED = "achievement_validated"  # External validation (A proof)
    REALITY_GROUNDED = "reality_grounded"      # Real-world proof (R proof)
    PROOF_REJECTED = "proof_rejected"          # User rejected claimed proof


class GEARDimensionType(str, Enum):
    """GEAR dimensions for targeted updates."""
    GEAR = "gear"
    EXPERIENCE = "experience"
    ACHIEVEMENTS = "achievements"
    REALITY = "reality"


# =============================================================================
# GEAR EVENT BUILDER
# =============================================================================

def gear_event(
    event_type: GEAREventType,
    message: str,
    paia_name: Optional[str] = None,
    dimension: Optional[GEARDimensionType] = None,
    component_type: Optional[str] = None,
    component_name: Optional[str] = None,
    inject: bool = False,  # Usually don't inject GEAR events to Claude
    visual: bool = True,
    **payload
) -> Event:
    """Build a GEAR event for SSE emission to frontend.

    Args:
        event_type: Type of GEAR event
        message: Human-readable message
        paia_name: Which PAIA this affects
        dimension: Which GEAR dimension (if dimension update)
        component_type: Component type (skills, mcps, etc.)
        component_name: Specific component name
        inject: Whether to inject into Claude (usually False for GEAR)
        visual: Whether to show terminal notification
        **payload: Additional event data
    """
    output = EventOutput(sse_emit=True)

    # Build SSE payload
    output.sse_data = {
        "gear_event_type": event_type.value,
        "paia_name": paia_name,
        "dimension": dimension.value if dimension else None,
        "component_type": component_type,
        "component_name": component_name,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        **payload
    }

    if visual:
        # Icon based on event type
        icon_map = {
            GEAREventType.GEAR_STATE_CHANGED: "⚙️",
            GEAREventType.DIMENSION_UPDATED: "📊",
            GEAREventType.LEVEL_UP: "🎮",
            GEAREventType.TIER_ADVANCED: "⬆️",
            GEAREventType.GOLDEN_CHANGED: "✨",
            GEAREventType.COMPONENT_ACCEPTED: "✅",
            GEAREventType.ACHIEVEMENT_VALIDATED: "🏆",
            GEAREventType.REALITY_GROUNDED: "🌍",
            GEAREventType.PROOF_REJECTED: "❌",
        }
        output.in_terminal = InTerminalObject(
            object_type=TerminalObjectType.NOTIFICATION,
            content=message,
            icon=icon_map.get(event_type, "⚙️"),
            duration_seconds=2.0
        )

    if inject:
        output.hook_injection = HookInjection(
            message=message,
            injection_type=InjectionType.SYSTEM_REMINDER,
            source="gear",
            event_name=event_type.value
        )

    return Event(
        source=EventSource.SYSTEM,  # GEAR is system-level
        name=event_type.value,
        payload=output.sse_data,
        output=output
    )


# =============================================================================
# OUTBOUND: GEAR → Events → Frontend
# =============================================================================

@dataclass
class GEARSnapshot:
    """Snapshot of GEAR state for emission."""
    paia_name: str
    gear_score: int
    experience_score: int
    achievements_score: int
    reality_score: int
    overall: int
    level: int
    phase: str
    total_points: int


def emit_gear_state(router, paia_name: str, gear_state) -> None:
    """Emit full GEAR state to frontend via SSE.

    Args:
        router: EventRouter instance
        paia_name: PAIA name
        gear_state: GEAR model instance from paia-builder
    """
    event = gear_event(
        event_type=GEAREventType.GEAR_STATE_CHANGED,
        message=f"GEAR state updated for {paia_name}",
        paia_name=paia_name,
        # Include full state in payload
        gear_score=gear_state.gear.score,
        experience_score=gear_state.experience.score,
        achievements_score=gear_state.achievements.score,
        reality_score=gear_state.reality.score,
        overall=gear_state.overall,
        level=gear_state.level,
        phase=gear_state.phase.value if hasattr(gear_state.phase, 'value') else str(gear_state.phase),
        total_points=gear_state.total_points,
    )
    router.route(event)
    logger.info(f"Emitted GEAR state for {paia_name}: L{gear_state.level} {gear_state.overall}%")


def emit_dimension_update(
    router,
    paia_name: str,
    dimension: GEARDimensionType,
    old_score: int,
    new_score: int,
    note: Optional[str] = None
) -> None:
    """Emit single dimension update to frontend."""
    event = gear_event(
        event_type=GEAREventType.DIMENSION_UPDATED,
        message=f"{paia_name} {dimension.value}: {old_score} → {new_score}",
        paia_name=paia_name,
        dimension=dimension,
        old_score=old_score,
        new_score=new_score,
        note=note,
    )
    router.route(event)


def emit_level_up(router, paia_name: str, old_level: int, new_level: int) -> None:
    """Emit level up event to frontend."""
    event = gear_event(
        event_type=GEAREventType.LEVEL_UP,
        message=f"{paia_name} LEVEL UP! {old_level} → {new_level}",
        paia_name=paia_name,
        old_level=old_level,
        new_level=new_level,
        visual=True,
    )
    router.route(event)


def emit_tier_advanced(
    router,
    paia_name: str,
    component_type: str,
    component_name: str,
    old_tier: str,
    new_tier: str
) -> None:
    """Emit component tier advancement to frontend."""
    event = gear_event(
        event_type=GEAREventType.TIER_ADVANCED,
        message=f"{component_name} ({component_type}): {old_tier} → {new_tier}",
        paia_name=paia_name,
        component_type=component_type,
        component_name=component_name,
        old_tier=old_tier,
        new_tier=new_tier,
    )
    router.route(event)


# =============================================================================
# INBOUND: Frontend → Events → GEAR (Proof Updates)
# =============================================================================

@dataclass
class AcceptanceEvent:
    """Inbound acceptance event from frontend."""
    event_type: GEAREventType
    paia_name: str
    component_type: Optional[str] = None
    component_name: Optional[str] = None
    dimension: Optional[GEARDimensionType] = None
    proof_note: Optional[str] = None
    accepted: bool = True


class GEARProofHandler:
    """Handles inbound proof events from frontend.

    Frontend sends acceptance events when user:
    - Accepts a component → G proof
    - Validates an achievement → A proof
    - Confirms reality grounding → R proof

    This handler updates GEAR state accordingly.
    """

    def __init__(self, paia_store: Callable[[str], Any]):
        """
        Args:
            paia_store: Callable that returns PAIA by name
        """
        self.paia_store = paia_store
        self._handlers: dict[GEAREventType, Callable] = {
            GEAREventType.COMPONENT_ACCEPTED: self._handle_component_accepted,
            GEAREventType.ACHIEVEMENT_VALIDATED: self._handle_achievement_validated,
            GEAREventType.REALITY_GROUNDED: self._handle_reality_grounded,
            GEAREventType.PROOF_REJECTED: self._handle_proof_rejected,
        }

    def handle(self, event: AcceptanceEvent) -> bool:
        """Handle an inbound acceptance event.

        Returns True if handled successfully.
        """
        handler = self._handlers.get(event.event_type)
        if not handler:
            logger.warning(f"No handler for event type: {event.event_type}")
            return False

        try:
            return handler(event)
        except Exception as e:
            logger.exception(f"Error handling {event.event_type}: {e}")
            return False

    def _handle_component_accepted(self, event: AcceptanceEvent) -> bool:
        """User accepted a component → G proof.

        Accepting a component confirms it EXISTS and is VALID gear.
        """
        paia = self.paia_store(event.paia_name)
        if not paia:
            logger.error(f"PAIA not found: {event.paia_name}")
            return False

        if event.accepted:
            # Component accepted = gear exists
            # This could trigger tier advancement or golden status change
            note = f"Component accepted: {event.component_type}/{event.component_name}"
            if event.proof_note:
                note += f" - {event.proof_note}"
            paia.gear_state.gear.notes.append(note)
            logger.info(f"G proof: {event.component_name} accepted")

        return True

    def _handle_achievement_validated(self, event: AcceptanceEvent) -> bool:
        """External validation received → A proof.

        Someone else used/validated this = achievement externally confirmed.
        """
        paia = self.paia_store(event.paia_name)
        if not paia:
            return False

        if event.accepted:
            note = f"Achievement validated: {event.component_type}/{event.component_name}"
            if event.proof_note:
                note += f" - {event.proof_note}"
            paia.gear_state.achievements.notes.append(note)
            logger.info(f"A proof: {event.component_name} validated externally")

        return True

    def _handle_reality_grounded(self, event: AcceptanceEvent) -> bool:
        """Real-world proof received → R proof.

        Something changed in the real world as a result of this PAIA.
        """
        paia = self.paia_store(event.paia_name)
        if not paia:
            return False

        if event.accepted:
            note = f"Reality grounded: {event.proof_note or 'No details'}"
            paia.gear_state.reality.notes.append(note)
            logger.info(f"R proof: {event.paia_name} grounded in reality")

        return True

    def _handle_proof_rejected(self, event: AcceptanceEvent) -> bool:
        """User rejected a claimed proof.

        This means the proof was invalid - may need to regress tier/golden.
        """
        paia = self.paia_store(event.paia_name)
        if not paia:
            return False

        dimension = event.dimension
        if dimension:
            dim_obj = getattr(paia.gear_state, dimension.value)
            note = f"REJECTED: {event.proof_note or 'No reason given'}"
            dim_obj.notes.append(note)
            logger.warning(f"Proof rejected for {event.paia_name}: {event.proof_note}")

        return True


# =============================================================================
# HTTP ENDPOINT HELPERS (for http_server.py integration)
# =============================================================================

def parse_acceptance_event(data: dict) -> AcceptanceEvent:
    """Parse incoming JSON into AcceptanceEvent.

    Expected JSON format from frontend:
    {
        "event_type": "component_accepted",
        "paia_name": "my-paia",
        "component_type": "skills",
        "component_name": "my-skill",
        "accepted": true,
        "proof_note": "User confirmed component works"
    }
    """
    return AcceptanceEvent(
        event_type=GEAREventType(data["event_type"]),
        paia_name=data["paia_name"],
        component_type=data.get("component_type"),
        component_name=data.get("component_name"),
        dimension=GEARDimensionType(data["dimension"]) if data.get("dimension") else None,
        proof_note=data.get("proof_note"),
        accepted=data.get("accepted", True),
    )
