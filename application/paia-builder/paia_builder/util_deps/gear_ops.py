"""GEAR operations."""

from typing import Optional
from datetime import datetime
from ..models import PAIA, AchievementTier, calculate_level, ExperienceEvent, ExperienceEventType
from .components import get_all_components


def log_experience(
    paia: PAIA,
    event_type: ExperienceEventType,
    component_type: Optional[str] = None,
    component_name: Optional[str] = None,
    details: str = "",
    gear_context: Optional[str] = None,
    achievement_context: Optional[str] = None,
    reality_context: Optional[str] = None,
) -> ExperienceEvent:
    """Log an experience event to the PAIA's timeline.

    E = Experience = the timeline of doing.
    Every action IS an experience event.
    G is the OUTPUT of E - cannot have G without E having happened.
    """
    event = ExperienceEvent(
        event_type=event_type,
        timestamp=datetime.now(),
        component_type=component_type,
        component_name=component_name,
        details=details,
        gear_context=gear_context,
        achievement_context=achievement_context,
        reality_context=reality_context,
    )
    paia.gear_state.experience_events.append(event)
    return event


def recalculate_points(paia: PAIA, legendary_count: int = 0) -> int:
    """Recalculate total points from all component tiers."""
    components = get_all_components(paia)
    tier_points = sum(c.points for c in components)

    if legendary_count == 0:
        legendary_count = sum(1 for c in components if c.tier == AchievementTier.LEGENDARY)

    legendary_bonus = legendary_count * 1_000_000
    total = tier_points + legendary_bonus
    paia.gear_state.total_points = total
    paia.gear_state.level = calculate_level(total)
    return total


def sync_gear(paia: PAIA) -> None:
    """Derive GEAR scores from actual data. E produces G.

    GEAR IS FRACTAL:
    G = made of EAR (components are output of experience)
    E = made of GAR (experience events involve gear, achievements, reality)
    A = made of GER (achievements validate gear through experience)
    R = made of GEA (reality grounds it all)
    """
    components = get_all_components(paia)
    events = paia.gear_state.experience_events
    total_components = len(components)
    total_events = len(events)

    # E = Experience: derived from experience_events timeline
    # More events = more experience. Also weight by recency.
    if total_events > 0:
        base_exp = min(50, total_events * 2)  # 2 pts per event, cap at 50
        # Recency bonus: events in last 7 days get bonus
        recent = sum(1 for e in events if (datetime.now() - e.timestamp).days < 7)
        recency_bonus = min(30, recent * 3)
        # Variety bonus: different event types
        unique_types = len(set(e.event_type for e in events))
        variety_bonus = min(20, unique_types * 5)
        exp_score = min(100, base_exp + recency_bonus + variety_bonus)
        paia.gear_state.experience.set_score(exp_score, f"events:{total_events}")
    else:
        paia.gear_state.experience.set_score(0)

    # G = Gear: OUTPUT of E. Can't have G without E.
    # Score based on components, but only if experience events exist
    if total_components > 0 and total_events > 0:
        gear_score = min(100, total_components)
        tier_counts = {tier: 0 for tier in AchievementTier}
        for c in components:
            tier_counts[c.tier] += 1
        legendary_count = tier_counts[AchievementTier.LEGENDARY]
        breakdown = [f"{t.value}:{n}" for t, n in tier_counts.items() if n > 0]
        paia.gear_state.gear.notes = [f"total:{total_components}", f"breakdown:{','.join(breakdown)}"]
        paia.gear_state.gear.set_score(gear_score)
    elif total_components > 0:
        # Components exist but no experience - shouldn't happen, but handle gracefully
        paia.gear_state.gear.set_score(min(100, total_components), "warning:no_experience_events")
        legendary_count = sum(1 for c in components if c.tier == AchievementTier.LEGENDARY)
    else:
        legendary_count = 0

    # A = Achievements: tier progression (validated through experience)
    if total_components > 0:
        tier_weights = {
            AchievementTier.NONE: 0, AchievementTier.COMMON: 1, AchievementTier.UNCOMMON: 2,
            AchievementTier.RARE: 3, AchievementTier.EPIC: 4, AchievementTier.LEGENDARY: 5,
        }
        tier_sum = sum(tier_weights[c.tier] for c in components)
        max_tier_sum = total_components * 5
        achievements_score = int((tier_sum / max_tier_sum) * 100) if max_tier_sum > 0 else 0
        paia.gear_state.achievements.set_score(achievements_score)

    # R = Reality: still self-reported (external validation)
    recalculate_points(paia, legendary_count)


def update_gear_dimension(paia: PAIA, dimension: str, score: int, note: Optional[str] = None) -> str:
    """Update a GEAR dimension score."""
    dim = getattr(paia.gear_state, dimension, None)
    if not dim:
        return f"Invalid dimension: {dimension}"
    dim.set_score(score, note)
    return f"{dimension}: {dim.bar()}"
