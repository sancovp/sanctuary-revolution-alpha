"""Component operations."""

from typing import Optional, List, Dict, Any
from ..models import PAIA, ComponentBase, AchievementTier, GoldenStatus
from .constants import COMPONENT_TYPES


def find_component(paia: PAIA, comp_type: str, name: str) -> Optional[ComponentBase]:
    """Find component by type and name."""
    for comp in getattr(paia, comp_type, []):
        if comp.name == name:
            return comp
    return None


def get_all_components(paia: PAIA) -> List[ComponentBase]:
    """Get all components as flat list."""
    return (paia.skills + paia.mcps + paia.hooks + paia.commands +
            paia.agents + paia.personas + paia.plugins + paia.flights +
            paia.metastacks + paia.giint_blueprints + paia.operadic_flows +
            paia.frontend_integrations + paia.automations +
            paia.agent_gans + paia.agent_duos + paia.system_prompts)


def component_summary(paia: PAIA) -> Dict[str, Dict[str, int]]:
    """Summary of components by type and tier."""
    summary = {}
    for comp_type in COMPONENT_TYPES:
        comps = getattr(paia, comp_type)
        by_tier = {}
        for tier in AchievementTier:
            count = sum(1 for c in comps if c.tier == tier)
            if count > 0:
                by_tier[tier.value] = count
        if by_tier:
            summary[comp_type] = by_tier
    return summary


def golden_summary(paia: PAIA) -> Dict[str, int]:
    """Count components by goldenization status."""
    counts = {s.value: 0 for s in GoldenStatus}
    for c in get_all_components(paia):
        counts[c.golden.value] += 1
    return counts
