"""Omnisanc State Machine - Course state tracking for PAIAs.

The OMNISANC state machine tracks where a PAIA is in its journey:

    HOME → MISSION → STARPORT → SESSION → LANDING → HOME

State file: /tmp/heaven_data/omnisanc_core/.course_state

This module provides types and helpers for the harness to track PAIA state
via websocket stream events from the container command API.
"""

import os
import json
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


class OmnisancPhase(str, Enum):
    """The phases of the OMNISANC state machine."""
    HOME = "HOME"
    MISSION = "MISSION"  # Explicit mission active
    STARPORT = "STARPORT"  # Phase 1: Flight config selection
    SESSION = "SESSION"  # Tools unlocked, actual work
    LANDING = "LANDING"  # Phase 2 (STARPORT 2): 3-step review sequence


class LandingStep(str, Enum):
    """The 3 steps of the LANDING phase."""
    PENDING = "PENDING"  # needs_review=True, no steps done
    LANDING_ROUTINE = "LANDING_ROUTINE"  # Step 1
    SESSION_REVIEW = "SESSION_REVIEW"  # Step 2
    GIINT_RESPOND = "GIINT_RESPOND"  # Step 3
    COMPLETE = "COMPLETE"  # All 3 done, returning to HOME


@dataclass
class CourseState:
    """Mirror of OMNISANC's course state from .course_state file.

    This is the full state that gets passed via websocket stream events
    from the container command API.
    """
    # Core state
    course_plotted: bool = False
    projects: List[str] = field(default_factory=list)
    flight_selected: bool = False
    waypoint_step: int = 0
    session_active: bool = False

    # Session shields
    session_end_shield_count: int = 1
    session_shielded: bool = True

    # Mission tracking
    mission_active: bool = False
    mission_id: Optional[str] = None
    mission_step: int = 0

    # Orientation
    last_oriented: Optional[str] = None
    description: Optional[str] = None

    # STARPORT categorization (Phase 1)
    domain: str = "HOME"
    subdomain: Optional[str] = None
    process: Optional[str] = None

    # LANDING phase (Phase 2 / STARPORT 2)
    needs_review: bool = False
    landing_routine_called: bool = False
    session_review_called: bool = False
    giint_respond_called: bool = False

    @property
    def phase(self) -> OmnisancPhase:
        """Determine current phase from state flags."""
        if self.needs_review:
            return OmnisancPhase.LANDING
        if self.session_active:
            return OmnisancPhase.SESSION
        if self.course_plotted:
            if self.mission_active:
                return OmnisancPhase.MISSION
            return OmnisancPhase.STARPORT
        return OmnisancPhase.HOME

    @property
    def landing_step(self) -> LandingStep:
        """Determine current LANDING step if in LANDING phase."""
        if not self.needs_review:
            return LandingStep.COMPLETE
        if self.giint_respond_called:
            return LandingStep.COMPLETE
        if self.session_review_called:
            return LandingStep.GIINT_RESPOND
        if self.landing_routine_called:
            return LandingStep.SESSION_REVIEW
        return LandingStep.PENDING

    @property
    def mode(self) -> str:
        """Get the mode string (HOME, JOURNEY_MISSION, JOURNEY_SESSION)."""
        if not self.course_plotted:
            return "HOME"
        if self.mission_active:
            return "JOURNEY_MISSION"
        return "JOURNEY_SESSION"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CourseState":
        """Create from dictionary (e.g., from JSON or websocket event)."""
        return cls(
            course_plotted=data.get("course_plotted", False),
            projects=data.get("projects", []),
            flight_selected=data.get("flight_selected", False),
            waypoint_step=data.get("waypoint_step", 0),
            session_active=data.get("session_active", False),
            session_end_shield_count=data.get("session_end_shield_count", 1),
            session_shielded=data.get("session_shielded", True),
            mission_active=data.get("mission_active", False),
            mission_id=data.get("mission_id"),
            mission_step=data.get("mission_step", 0),
            last_oriented=data.get("last_oriented"),
            description=data.get("description"),
            domain=data.get("domain", "HOME"),
            subdomain=data.get("subdomain"),
            process=data.get("process"),
            needs_review=data.get("needs_review", False),
            landing_routine_called=data.get("landing_routine_called", False),
            session_review_called=data.get("session_review_called", False),
            giint_respond_called=data.get("giint_respond_called", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "course_plotted": self.course_plotted,
            "projects": self.projects,
            "flight_selected": self.flight_selected,
            "waypoint_step": self.waypoint_step,
            "session_active": self.session_active,
            "session_end_shield_count": self.session_end_shield_count,
            "session_shielded": self.session_shielded,
            "mission_active": self.mission_active,
            "mission_id": self.mission_id,
            "mission_step": self.mission_step,
            "last_oriented": self.last_oriented,
            "description": self.description,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "process": self.process,
            "needs_review": self.needs_review,
            "landing_routine_called": self.landing_routine_called,
            "session_review_called": self.session_review_called,
            "giint_respond_called": self.giint_respond_called,
        }


# State file location
HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
COURSE_STATE_FILE = Path(HEAVEN_DATA_DIR) / "omnisanc_core" / ".course_state"


def load_course_state() -> CourseState:
    """Load current course state from file (for local/host access).

    For container PAIAs, state comes via websocket - use CourseState.from_dict().
    """
    try:
        if COURSE_STATE_FILE.exists():
            with open(COURSE_STATE_FILE, 'r') as f:
                return CourseState.from_dict(json.load(f))
    except Exception:
        pass
    return CourseState()


def get_phase() -> OmnisancPhase:
    """Quick check: what phase are we in?"""
    return load_course_state().phase


def is_home() -> bool:
    """Are we in HOME mode?"""
    return get_phase() == OmnisancPhase.HOME


def is_in_session() -> bool:
    """Are we in an active SESSION?"""
    return get_phase() == OmnisancPhase.SESSION


def is_landing() -> bool:
    """Are we in LANDING phase?"""
    return get_phase() == OmnisancPhase.LANDING
