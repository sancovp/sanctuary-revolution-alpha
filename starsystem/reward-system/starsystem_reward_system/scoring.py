#!/usr/bin/env python3
"""
Reward System - Stats aggregation and fitness function for OMNISANC self-play

Reads event registries and computes:
- Stats (completion rates, error rates, durations)
- Rewards (per-event, per-session, per-mission)
- Fitness function (overall usage reward)
- XP/Level system

This file is edited directly to optimize the reward system (self-play).
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

# ============================================================================
# EVENT REWARDS - Base scores for individual events
# ============================================================================

EVENT_REWARDS = {
    # Mission events (highest value)
    "mission_start": 100,
    "mission_report_progress": 50,  # per step completed
    "mission_complete": 500,
    "mission_inject_step": -20,  # penalty for course correction
    "mission_request_extraction": -200,  # penalty for abandonment

    # Session events (medium value)
    "start_starlog": 20,
    "end_starlog": 100,  # bonus for proper completion
    "update_debug_diary": 5,

    # Waypoint events
    "start_waypoint_journey": 10,
    "navigate_to_next_waypoint": 15,  # per waypoint
    "abort_waypoint_journey": -30,

    # Home events (low value - encourages progression)
    "plot_course": 50,  # reward for starting journey

    # Quality penalties
    "omnisanc_error": -10,
    "validation_block": -5,  # attempted disallowed tool
}

# ============================================================================
# XP MULTIPLIERS
# ============================================================================

HOME_MULTIPLIER = 1.0
SESSION_MULTIPLIER = 3.0
MISSION_MULTIPLIER = 10.0

# ============================================================================
# FITNESS CONDITIONS - Dynamically added to optimize score
# ============================================================================

FITNESS_CONDITIONS = [
    "complete_sessions",  # +100 per completed session
    "complete_missions",  # +500 per completed mission
    "low_error_rate",     # +quality_multiplier
]

# ============================================================================
# STATS AGGREGATION
# ============================================================================

def get_events_from_registry(registry_service, registry_base: str, date: str) -> List[Dict]:
    """
    Get all events from a specific registry for a date.

    Args:
        registry_service: RegistryService instance
        registry_base: "home_events", "mission_events", or "session_events"
        date: Date string (YYYY-MM-DD)

    Returns:
        List of event dictionaries
    """
    day_registry_name = f"{registry_base}_{date}"
    events = []

    if registry_service.simple_service.registry_exists(day_registry_name):
        all_data = registry_service.get_all(day_registry_name)

        for event_key, event_data in all_data.items():
            if event_key != "_meta" and isinstance(event_data, dict):
                event_data["_registry"] = registry_base
                event_data["_key"] = event_key
                events.append(event_data)

    return events


def compute_stats(registry_service, start_date: str, end_date: str = None) -> Dict[str, Any]:
    """
    Compute aggregated stats from event registries.

    Args:
        registry_service: RegistryService instance
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to start_date

    Returns:
        Dictionary of computed statistics
    """
    if end_date is None:
        end_date = start_date

    # For now, just handle single day (can expand later)
    all_events = []

    for registry_base in ["home_events", "mission_events", "session_events"]:
        events = get_events_from_registry(registry_service, registry_base, start_date)
        all_events.extend(events)

    # Sort by timestamp
    all_events.sort(key=lambda x: x.get("timestamp", ""))

    # Count tools
    def count_tool(tool_name: str, **filters) -> int:
        count = 0
        for event in all_events:
            if event.get("tool_name", "").endswith(tool_name):
                # Check filters
                match = True
                for key, value in filters.items():
                    if event.get(key) != value:
                        match = False
                        break
                if match:
                    count += 1
        return count

    # Mission metrics
    missions_started = count_tool("mission_start")
    missions_extracted = count_tool("mission_request_extraction")
    missions_completed = count_tool("mission_report_progress")  # TODO: check if final step

    # Session metrics
    sessions_started = count_tool("start_starlog")
    sessions_ended = count_tool("end_starlog")

    # Waypoint metrics
    waypoints_started = count_tool("start_waypoint_journey")
    waypoints_aborted = count_tool("abort_waypoint_journey")

    # Error metrics
    omnisanc_errors = len([e for e in all_events if "omnisanc_error" in e.get("reason", "").lower()])
    validation_blocks = len([e for e in all_events if not e.get("allowed", True)])

    # Compute rates
    mission_extraction_rate = missions_extracted / missions_started if missions_started > 0 else 0
    mission_completion_rate = missions_completed / missions_started if missions_started > 0 else 0
    session_completion_rate = sessions_ended / sessions_started if sessions_started > 0 else 0
    waypoint_abandon_rate = waypoints_aborted / waypoints_started if waypoints_started > 0 else 0

    stats = {
        "date": start_date,
        "total_events": len(all_events),

        "mission": {
            "started": missions_started,
            "extracted": missions_extracted,
            "completed": missions_completed,
            "extraction_rate": mission_extraction_rate,
            "completion_rate": mission_completion_rate,
        },

        "session": {
            "started": sessions_started,
            "ended": sessions_ended,
            "completion_rate": session_completion_rate,
            "omnisanc_errors": omnisanc_errors,
            "errors_per_session": omnisanc_errors / sessions_started if sessions_started > 0 else 0,
        },

        "waypoint": {
            "started": waypoints_started,
            "aborted": waypoints_aborted,
            "abandon_rate": waypoint_abandon_rate,
        },

        "quality": {
            "omnisanc_errors": omnisanc_errors,
            "validation_blocks": validation_blocks,
            "error_rate": (omnisanc_errors + validation_blocks) / len(all_events) if all_events else 0,
        }
    }

    return stats


# ============================================================================
# REWARD CALCULATION
# ============================================================================

def compute_event_reward(event: Dict) -> float:
    """
    Compute reward for a single event.

    Args:
        event: Event dictionary

    Returns:
        Reward score
    """
    tool_name = event.get("tool_name", "")
    allowed = event.get("allowed", True)
    reason = event.get("reason", "")

    # Check if tool matches any reward key
    for reward_key, reward_value in EVENT_REWARDS.items():
        if tool_name.endswith(reward_key):
            return reward_value

    # Check for error penalties
    if "omnisanc_error" in reason.lower():
        return EVENT_REWARDS["omnisanc_error"]

    if not allowed:
        return EVENT_REWARDS["validation_block"]

    # Default: no reward
    return 0.0


def compute_session_reward(session_events: List[Dict]) -> float:
    """
    Compute reward for a session.

    Args:
        session_events: List of events in the session

    Returns:
        Session reward score
    """
    # Sum event rewards
    base_reward = sum(compute_event_reward(event) for event in session_events)

    # Check for completion bonus
    has_start = any(e.get("tool_name", "").endswith("start_starlog") for e in session_events)
    has_end = any(e.get("tool_name", "").endswith("end_starlog") for e in session_events)

    completion_bonus = 100 if (has_start and has_end) else 0

    # Quality multiplier (1.0 - error_rate)
    errors = len([e for e in session_events if not e.get("allowed", True)])
    error_rate = errors / len(session_events) if session_events else 0
    quality_multiplier = 1.0 - error_rate

    session_reward = (base_reward + completion_bonus) * quality_multiplier * SESSION_MULTIPLIER

    return session_reward


def compute_mission_reward(mission_events: List[Dict]) -> float:
    """
    Compute reward for a mission (sum of session rewards).

    Args:
        mission_events: List of events in the mission

    Returns:
        Mission reward score
    """
    # For now, treat as one session (TODO: split by actual sessions)
    base_reward = sum(compute_event_reward(event) for event in mission_events)

    # Check for mission completion/extraction
    has_complete = any(e.get("tool_name", "").endswith("mission_report_progress") for e in mission_events)
    has_extraction = any(e.get("tool_name", "").endswith("mission_request_extraction") for e in mission_events)

    mission_completion_bonus = 500 if has_complete else 0
    mission_extraction_penalty = -500 if has_extraction else 0

    mission_reward = (base_reward + mission_completion_bonus + mission_extraction_penalty) * MISSION_MULTIPLIER

    return mission_reward


def compute_fitness(registry_service, date: str) -> Dict[str, Any]:
    """
    Compute fitness function (overall usage reward).

    Args:
        registry_service: RegistryService instance
        date: Date string (YYYY-MM-DD)

    Returns:
        Dictionary with fitness score and breakdown
    """
    # Get all events
    home_events = get_events_from_registry(registry_service, "home_events", date)
    session_events = get_events_from_registry(registry_service, "session_events", date)
    mission_events = get_events_from_registry(registry_service, "mission_events", date)

    # Compute rewards
    home_rewards = sum(compute_event_reward(e) for e in home_events) * HOME_MULTIPLIER
    session_rewards = compute_session_reward(session_events)
    mission_rewards = compute_mission_reward(mission_events)

    # Quality factor (from stats)
    all_events = home_events + session_events + mission_events
    errors = len([e for e in all_events if not e.get("allowed", True)])
    quality_factor = 1.0 - (errors / len(all_events) if all_events else 0)

    # Fitness = weighted sum * quality
    fitness = (home_rewards + session_rewards + mission_rewards) * quality_factor

    # Compute XP (total accumulated rewards)
    xp = home_rewards + session_rewards + mission_rewards

    # Level = Fitness score (rounded)
    level = int(fitness)

    return {
        "date": date,
        "fitness": fitness,
        "level": level,
        "xp": xp,
        "breakdown": {
            "home_rewards": home_rewards,
            "session_rewards": session_rewards,
            "mission_rewards": mission_rewards,
            "quality_factor": quality_factor,
        }
    }
