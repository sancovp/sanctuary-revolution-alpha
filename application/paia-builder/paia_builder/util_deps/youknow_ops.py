"""YOUKNOW integration operations."""

from ..models import PAIA, ComponentBase
from .constants import COMPONENT_TYPE_MAP


def register_component_in_youknow(paia: PAIA, component: ComponentBase, component_type: str) -> None:
    """Register a component in YOUKNOW ontology."""
    if not component.is_a:
        component.is_a = [component_type]
    elif component_type not in component.is_a:
        component.is_a.append(component_type)
    paia.youknow.add_entity(component)


def sync_to_youknow(paia: PAIA) -> int:
    """Sync all components to YOUKNOW. Returns count."""
    count = 0
    for attr, comp_type in COMPONENT_TYPE_MAP.items():
        for comp in getattr(paia, attr):
            register_component_in_youknow(paia, comp, comp_type)
            count += 1
    return count
