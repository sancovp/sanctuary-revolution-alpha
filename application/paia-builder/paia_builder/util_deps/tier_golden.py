"""Tier and golden status operations."""

from typing import Optional, Tuple
from datetime import datetime

from ..models import (
    ComponentBase, AchievementTier, GoldenStatus,
    TIER_POINTS, TIER_CONTRACTS, TIER_TO_VALIDATION
)


def get_next_tier(current: AchievementTier) -> Optional[AchievementTier]:
    """Get next tier in progression."""
    next_tiers = {
        AchievementTier.NONE: AchievementTier.COMMON,
        AchievementTier.COMMON: AchievementTier.UNCOMMON,
        AchievementTier.UNCOMMON: AchievementTier.RARE,
        AchievementTier.RARE: AchievementTier.EPIC,
        AchievementTier.EPIC: AchievementTier.LEGENDARY,
    }
    return next_tiers.get(current)


def advance_component_tier(comp: ComponentBase, fulfillment: str) -> Tuple[bool, str]:
    """Advance component tier. Returns (success, message)."""
    current = comp.tier
    next_tier = get_next_tier(current)
    if not next_tier:
        return False, f"{comp.name} is already LEGENDARY (max tier)"

    contract = TIER_CONTRACTS[next_tier]
    comp.tier = next_tier
    comp.validation_level = TIER_TO_VALIDATION[next_tier]
    comp.updated = datetime.now()
    comp.notes.append(f"[{next_tier.value}] CONTRACT: {contract}")
    comp.notes.append(f"[{next_tier.value}] FULFILLMENT: {fulfillment}")

    points_gained = TIER_POINTS[next_tier] - TIER_POINTS[current]
    message = f"{comp.name}: {current.value} → {next_tier.value} (+{points_gained} pts)\nContract: {contract}\nFulfillment: {fulfillment}"
    return True, message


def set_component_tier(comp: ComponentBase, tier: AchievementTier, note: Optional[str] = None) -> str:
    """Set component tier directly."""
    old_tier = comp.tier
    comp.tier = tier
    comp.validation_level = TIER_TO_VALIDATION[tier]
    comp.updated = datetime.now()
    if note:
        comp.notes.append(f"[set:{tier.value}] {note}")
    return f"{comp.name}: {old_tier.value} → {tier.value}"


def get_next_golden(current: GoldenStatus) -> Optional[GoldenStatus]:
    """Get next golden status."""
    next_status = {
        GoldenStatus.QUARANTINE: GoldenStatus.CRYSTAL,
        GoldenStatus.CRYSTAL: GoldenStatus.GOLDEN,
    }
    return next_status.get(current)


def advance_golden(comp: ComponentBase, note: Optional[str] = None) -> Tuple[bool, str]:
    """Advance golden status. Returns (success, message)."""
    current = comp.golden
    next_gold = get_next_golden(current)
    if not next_gold:
        return False, f"{comp.name} is already GOLDEN (max status)"

    comp.golden = next_gold
    comp.updated = datetime.now()
    if note:
        comp.notes.append(f"[{next_gold.value}] {note}")
    return True, f"{comp.name}: {current.value} → {next_gold.value}"


def regress_golden(comp: ComponentBase, reason: str) -> Tuple[bool, str]:
    """Regress golden status to quarantine."""
    old = comp.golden
    if old == GoldenStatus.QUARANTINE:
        return False, f"{comp.name} already in QUARANTINE"
    comp.golden = GoldenStatus.QUARANTINE
    comp.updated = datetime.now()
    comp.notes.append(f"[regress] {reason}")
    return True, f"{comp.name}: {old.value} → quarantine (reason: {reason})"
