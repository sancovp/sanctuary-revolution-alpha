"""
STARSYSTEM Reward System - Stats aggregation and fitness function

Reads event registries and computes:
- Stats (completion rates, error rates, durations)
- Rewards (per-event, per-session, per-mission)
- Fitness function (overall usage reward)
- XP/Level system
"""

from .scoring import (
    compute_fitness,
    compute_stats,
    get_events_from_registry,
    EVENT_REWARDS,
    HOME_MULTIPLIER,
    SESSION_MULTIPLIER,
    MISSION_MULTIPLIER
)

__all__ = [
    'compute_fitness',
    'compute_stats',
    'get_events_from_registry',
    'EVENT_REWARDS',
    'HOME_MULTIPLIER',
    'SESSION_MULTIPLIER',
    'MISSION_MULTIPLIER'
]
