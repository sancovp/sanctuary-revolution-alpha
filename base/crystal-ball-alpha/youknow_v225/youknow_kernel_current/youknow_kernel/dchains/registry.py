"""DeductionChain auto-registration — in-memory Python registry only.

Importing this module triggers registration of every DeductionChain instance
declared in any module that imports `register`. At fire time the dispatcher
looks up chains by (target_type, argument_name) and calls the bound callable.

Architectural note: this registry deliberately does NOT call out to CartON.
carton-mcp imports youknow_kernel (for system-type validation); the reverse
direction would create a circular dependency. If/when OWL individuals for
Deduction_Chain become useful (e.g. for a consistency-check pass), they
should land via the observation daemon queue (a separate process boundary),
not by importing carton from inside youknow.
"""

import logging
from typing import Callable, Dict, List, Tuple

from ..deduction_chain import DeductionChain

logger = logging.getLogger(__name__)

_REGISTRY: Dict[Tuple[str, str], List[Tuple[DeductionChain, Callable]]] = {}


def register(chain: DeductionChain, body: Callable) -> None:
    """Register a DeductionChain instance + its callable body.

    Adds to in-memory registry. No side effects beyond the registry mutation
    and a log line.
    """
    key = (chain.target_type, chain.argument_name or "__type_level__")
    _REGISTRY.setdefault(key, []).append((chain, body))
    logger.info(f"Registered DeductionChain: {chain.target_type}.{chain.argument_name}")


def get_chains(target_type: str, argument_name: str) -> List[Tuple[DeductionChain, Callable]]:
    """Look up chains attached to (target_type, argument_name)."""
    return _REGISTRY.get((target_type, argument_name), [])


def all_chains() -> Dict[Tuple[str, str], List[Tuple[DeductionChain, Callable]]]:
    """All registered chains (for diagnostics)."""
    return dict(_REGISTRY)
