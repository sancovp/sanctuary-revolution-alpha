"""SES (Short Exact Sequences) - The mathematical substrate for YOUKNOW validation.

This module provides:
- CategoryStructure: YOUKNOW's perception layer (objects + morphisms)
- SES validation: Exactness guarantees chains terminate
- llm_suggest: Passthrough shell - errors surface to the conversation

Key insight: llm_suggest doesn't call an API. WE are the oracle.
The compound intelligence system IS the reasoning layer.
"""

import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# CERTAINTY STATE - Epistemic self-awareness
# =============================================================================

class CertaintyState(str, Enum):
    """YOUKNOW's epistemic state."""
    SANCTUARY = "sanctuary"      # >0.8 - solid ground
    CAUTION = "caution"          # 0.5-0.8 - proceed carefully
    WASTELAND = "wasteland"      # <0.5 - lost coherence


# =============================================================================
# CATEGORY STRUCTURE - YOUKNOW's perception layer
# =============================================================================

class Morphism(BaseModel):
    """A morphism (arrow) between objects."""
    source: str
    target: str
    name: Optional[str] = None

    def __repr__(self):
        name = self.name or "→"
        return f"{self.source} {name} {self.target}"


class CategoryStructure(BaseModel):
    """What YOUKNOW perceives when given any structure.

    Fallback perception: even when YOUKNOW doesn't recognize
    something specific, it can always see objects + morphisms.
    """
    objects: List[str] = Field(default_factory=list)
    morphisms: List[Morphism] = Field(default_factory=list)

    # Inferred properties
    has_identity: bool = False
    has_composition: bool = False
    is_functor: bool = False

    def describe(self) -> str:
        """Describe what YOUKNOW perceives."""
        return f"""Category Structure:
  Objects: {self.objects}
  Morphisms: {[str(m) for m in self.morphisms]}
  Has identity: {self.has_identity}
  Has composition: {self.has_composition}
  Is functor: {self.is_functor}"""


# =============================================================================
# LLM_SUGGEST - The passthrough shell
# =============================================================================

def llm_suggest(context: str, error: str, choices: Optional[Dict[str, List[str]]] = None) -> str:
    """WE are the oracle. Just surface the error.

    This function doesn't call an API. It formats the error
    so the human+agent in the conversation can see it and respond.

    The "LLM reasoning" happens in the Claude Code session.
    """
    choice_str = ""
    if choices:
        choice_str = f"\n  Known choices: {list(choices.keys())}"

    return f"""
╔══════════════════════════════════════════════════════════════╗
║  YOUKNOW NEEDS INPUT                                         ║
╠══════════════════════════════════════════════════════════════╣
║  Context: {context[:50]}{'...' if len(context) > 50 else ''}
║  Error: {error}
║  {choice_str}
║
║  What should I do?
╚══════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# PROPERTY / ATTRIBUTE / UNIVERSAL PATTERN - Bounds-based validation
# =============================================================================

from typing import Generic, TypeVar, Callable

T = TypeVar("T")

class Attribute(BaseModel, Generic[T]):
    """A typed value with admissible range [low, high]."""
    value: Any  # T
    low: Any    # T
    high: Any   # T

    model_config = {"arbitrary_types_allowed": True}

    @property
    def ok(self) -> bool:
        return self.low <= self.value <= self.high


@dataclass
class Property(Generic[T]):
    """Named attribute with listeners (feedback hooks)."""
    name: str
    attr: Attribute[T]
    listeners: List[Callable[[T], None]] = field(default_factory=list)

    def set(self, new_val: T) -> None:
        self.attr.value = new_val
        if not self.attr.ok:
            raise ValueError(f"{self.name} out of range: {new_val}")
        for cb in self.listeners:
            cb(new_val)

    def on_change(self, cb: Callable[[T], None]) -> None:
        self.listeners.append(cb)


class UniversalPattern:
    """Base class for bounds-constrained patterns."""

    def __init__(self, **props: Property[Any]):
        self._props: Dict[str, Property[Any]] = props

    def prop(self, name: str) -> Property[Any]:
        return self._props[name]

    def values(self) -> Dict[str, Any]:
        return {k: p.attr.value for k, p in self._props.items()}


# =============================================================================
# SES LAYER - Short Exact Sequence for chain validation
# =============================================================================

class PropertyModule:
    """A module with dimensions per vertex."""

    def __init__(self, dims: Dict[str, int]):
        self.dims = dims
        self.total_dim = sum(dims.values())
        self._offsets = self._compute_offsets()

    def _compute_offsets(self) -> Dict[str, int]:
        offsets = {}
        idx = 0
        for v, d in self.dims.items():
            offsets[v] = idx
            idx += d
        return offsets

    def zero_vector(self) -> np.ndarray:
        return np.zeros((self.total_dim, 1))

    def basis_vector(self, vertex: str, index: int) -> np.ndarray:
        vec = np.zeros((self.total_dim, 1))
        start = self._offsets[vertex]
        vec[start + index, 0] = 1
        return vec


class InclusionMap:
    """Injective linear map between PropertyModules."""

    def __init__(self, source: PropertyModule, target: PropertyModule, matrix: np.ndarray):
        self.S = source
        self.T = target
        self.g = matrix
        self._validate()

    def _validate(self):
        assert self.g.shape == (self.T.total_dim, self.S.total_dim), \
            "Inclusion map dimensions don't match"

    def is_injective(self, tol: float = 1e-8) -> bool:
        rank = np.linalg.matrix_rank(self.g, tol)
        return rank == self.S.total_dim


class ExactSequenceValidator:
    """Validates exactness of short exact sequences."""

    @staticmethod
    def compute_quotient_projection(inc: InclusionMap, tol: float = 1e-8) -> np.ndarray:
        """Compute P: T -> Q = T / im(g) as left nullspace of g."""
        U, S_vals, Vt = np.linalg.svd(inc.g.T, full_matrices=True)
        rank = np.linalg.matrix_rank(inc.g, tol)
        nullspace = Vt[rank:].copy()
        return nullspace

    @staticmethod
    def check_exactness(inc: InclusionMap, P: np.ndarray, tol: float = 1e-8) -> bool:
        if not inc.is_injective(tol):
            return False
        if not np.allclose(P @ inc.g, 0, atol=tol):
            return False
        if np.linalg.matrix_rank(P, tol) != P.shape[0]:
            return False
        return True


class SESLayer:
    """A single short exact sequence layer."""

    def __init__(self, source: PropertyModule, target: PropertyModule, inc_matrix: np.ndarray):
        self.source = source
        self.target = target
        self.inc_map = InclusionMap(source, target, inc_matrix)
        self.projection = ExactSequenceValidator.compute_quotient_projection(self.inc_map)

        if not ExactSequenceValidator.check_exactness(self.inc_map, self.projection):
            raise ValueError("Layer failed exactness")

    @property
    def quotient_dim(self) -> int:
        return self.projection.shape[0]


class SESResolver:
    """Chains SES layers until quotient_dim == 0 (termination)."""

    def __init__(self, base_dims: Dict[str, int]):
        self.layers: List[SESLayer] = []
        self.current_module = PropertyModule(base_dims)
        self.certainty: float = 1.0
        self.checkpoint_stack: List[PropertyModule] = []

    def add_layer(self, next_dims: Dict[str, int], inc_matrix: np.ndarray) -> str:
        """Add a layer. Returns error message if failed."""
        try:
            next_module = PropertyModule(next_dims)
            layer = SESLayer(self.current_module, next_module, inc_matrix)
            self.layers.append(layer)
            self.checkpoint_stack.append(self.current_module)
            self.current_module = next_module
            return ""
        except ValueError as e:
            logger.error("SES layer failed: %s\n%s", e, traceback.format_exc())
            return llm_suggest(
                context=f"Adding SES layer with dims {next_dims}",
                error=str(e)
            )

    def complete(self) -> bool:
        """Is the resolution complete? (quotient_dim == 0)"""
        return bool(self.layers and self.layers[-1].quotient_dim == 0)

    def get_certainty_state(self) -> CertaintyState:
        """What's the epistemic state?"""
        if self.certainty > 0.8:
            return CertaintyState.SANCTUARY
        elif self.certainty >= 0.5:
            return CertaintyState.CAUTION
        else:
            return CertaintyState.WASTELAND

    def wasteland_warning(self) -> str:
        """Generate warning when entering wasteland."""
        return f"""
⚠️  CERTAINTY: {self.certainty:.2f} - APPROACHING WASTELAND

Current state:
  Layers: {len(self.layers)}
  Last quotient_dim: {self.layers[-1].quotient_dim if self.layers else 'N/A'}
  Checkpoints available: {len(self.checkpoint_stack)}

Options:
  [R] Revert to last checkpoint
  [C] Continue (risky - may not cohere)
  [S] Stop here, you figure it out

(R/C/S)?
"""

    def revert(self) -> bool:
        """Revert to last checkpoint."""
        if self.checkpoint_stack:
            self.current_module = self.checkpoint_stack.pop()
            if self.layers:
                self.layers.pop()
            self.certainty = min(1.0, self.certainty + 0.2)
            return True
        return False


# =============================================================================
# VALIDATE_PATTERN_OF_ISA - The core validation function
# =============================================================================

class ValidationResult(BaseModel):
    """Result of validating an is_a chain."""
    valid: bool
    chain: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    message: str = ""
    certainty: float = 1.0


def validate_pattern_of_isa(
    entity_name: str,
    entities: Dict[str, Any],
    visited: Optional[set] = None
) -> ValidationResult:
    """Validate that entity traces to pattern_of_isa.

    Uses simple graph traversal. SES validates the structure is exact.
    Returns clear errors when chain breaks.
    """
    if visited is None:
        visited = set()

    # Root case
    if entity_name == "pattern_of_isa":
        return ValidationResult(
            valid=True,
            chain=["pattern_of_isa"],
            message="Reached root: pattern_of_isa"
        )

    # Cycle detection
    if entity_name in visited:
        return ValidationResult(
            valid=False,
            chain=list(visited),
            message=llm_suggest(
                context=f"Validating chain for {entity_name}",
                error=f"Cycle detected: {entity_name} already in chain {visited}"
            )
        )

    visited.add(entity_name)

    # Entity doesn't exist
    if entity_name not in entities:
        return ValidationResult(
            valid=False,
            missing=[entity_name],
            message=llm_suggest(
                context=f"Validating {entity_name}",
                error=f"Entity '{entity_name}' doesn't exist in ontology"
            )
        )

    entity = entities[entity_name]

    # No is_a chain
    if not hasattr(entity, 'is_a') or not entity.is_a:
        return ValidationResult(
            valid=False,
            chain=[entity_name],
            message=llm_suggest(
                context=f"Validating {entity_name}",
                error=f"Entity '{entity_name}' has no is_a chain to root"
            )
        )

    # Recursively validate parents
    all_missing = []
    for parent in entity.is_a:
        result = validate_pattern_of_isa(parent, entities, visited.copy())
        if result.valid:
            return ValidationResult(
                valid=True,
                chain=[entity_name] + result.chain,
                message=f"Valid chain: {entity_name} → {' → '.join(result.chain)}"
            )
        all_missing.extend(result.missing)

    return ValidationResult(
        valid=False,
        chain=[entity_name],
        missing=all_missing,
        message=llm_suggest(
            context=f"Validating {entity_name}",
            error=f"No valid chain to pattern_of_isa. Missing: {all_missing}"
        )
    )
