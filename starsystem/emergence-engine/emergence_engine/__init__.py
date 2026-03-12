"""
Three-Pass State Tracker - State management for the 3-pass systematic thinking methodology
"""

from .core import (
    ThreePassState,
    ThreePassTracker,
    start_journey,
    get_current_state,
    next_phase,
    get_instructions,
    get_status,
    complete_journey,
    abandon_journey,
    get_contextual_prompt,
    explore_methodology,
    inject_3pass_structure,
    get_phase_file_path
)

__all__ = [
    "ThreePassState", 
    "ThreePassTracker",
    "start_journey",
    "get_current_state", 
    "next_phase",
    "get_instructions",
    "get_status",
    "complete_journey",
    "abandon_journey",
    "get_contextual_prompt",
    "explore_methodology",
    "inject_3pass_structure",
    "get_phase_file_path"
]