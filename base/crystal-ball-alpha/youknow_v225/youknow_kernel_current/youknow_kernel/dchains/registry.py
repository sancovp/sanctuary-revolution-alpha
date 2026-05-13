"""DeductionChain auto-registration.

Importing this module triggers registration of every DeductionChain instance
declared in any module that imports `register`. The registry is the Python-side
mirror of the OWL Deduction_Chain individuals.

The OWL IS the registry — this Python-side dict is the runtime lookup cache.
At fire time we look up by (target_type, argument_name) and call the bound
callable. The OWL individual is emitted best-effort via CartON for visibility
in the consistency-check pass (Task #12).
"""

import logging
from typing import Callable, Dict, List, Tuple

from ..deduction_chain import DeductionChain

logger = logging.getLogger(__name__)

_REGISTRY: Dict[Tuple[str, str], List[Tuple[DeductionChain, Callable]]] = {}


def register(chain: DeductionChain, body: Callable) -> None:
    """Register a DeductionChain instance + its callable body.

    Adds to in-memory registry. Best-effort emits OWL individual via CartON.
    The in-memory registry is sufficient for fire-time lookup; the OWL emission
    is for cross-system visibility (consistency check, observability).
    """
    key = (chain.target_type, chain.argument_name or "__type_level__")
    _REGISTRY.setdefault(key, []).append((chain, body))
    logger.info(f"Registered DeductionChain: {chain.target_type}.{chain.argument_name}")
    _emit_owl_individual(chain)


def get_chains(target_type: str, argument_name: str) -> List[Tuple[DeductionChain, Callable]]:
    """Look up chains attached to (target_type, argument_name)."""
    return _REGISTRY.get((target_type, argument_name), [])


def all_chains() -> Dict[Tuple[str, str], List[Tuple[DeductionChain, Callable]]]:
    """All registered chains (for diagnostics)."""
    return dict(_REGISTRY)


def _emit_owl_individual(chain: DeductionChain) -> None:
    """Reflect this chain as an OWL individual via CartON.

    Best-effort. Failures logged but not raised — the in-memory registry still
    works without the OWL side. The reflection step is what makes the chain
    visible to YOUKNOW's consistency-check command.
    """
    try:
        from carton_mcp.add_concept_tool import add_concept_tool_func  # type: ignore

        concept_name = f"Deduction_Chain_{chain.target_type}_{chain.argument_name or 'TypeLevel'}"
        description = (
            f"D-chain for {chain.target_type}.{chain.argument_name}: {chain.description}. "
            f"Body: {chain.body}. Body type: {chain.body_type}."
        )
        add_concept_tool_func(
            concept_name=concept_name,
            description=description,
            relationships=[
                {"relationship": "is_a", "related": ["Deduction_Chain"]},
                {"relationship": "part_of", "related": ["Starsystem_Home_God_Gnosys_Plugin_V2"]},
                {"relationship": "instantiates", "related": ["Deduction_Chain"]},
            ],
            hide_youknow=True,
        )
    except Exception as e:
        logger.warning(
            f"Could not emit OWL individual for {chain.target_type}.{chain.argument_name}: {e}"
        )
