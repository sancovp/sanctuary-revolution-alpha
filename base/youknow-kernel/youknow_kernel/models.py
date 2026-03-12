"""YOUKNOW Models - Data structures only.

No logic here. Just Pydantic models and enums.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# =============================================================================
# CORE ENUMS
# =============================================================================

class InteractionMode(str, Enum):
    """YOUKNOW's interaction state - is it being defined or validating?"""
    DEFINING = "defining"
    VALIDATING = "validating"


class ValidationLevel(str, Enum):
    """The spectrum from arbitrary string to fully reified entity.

    THIS IS THE CORE SENTENCE IN ACTION:
    embodies  → EMBODIES  (declare you think you know something)
    manifests → MANIFESTS (try to type it)
    reifies   → REIFIES   (succeeded - is_a programs = EXECUTING)
    produces → PRODUCES (golden, can produce more)
    """
    EMBODIES = "embodies"
    MANIFESTS = "manifests"
    REIFIES = "reifies"
    PRODUCES = "produces"


class SelfSimulationLevel(str, Enum):
    """The emanation hierarchy - how self-aware is this entity?"""
    NONE = "none"
    EMANATION = "emanation"
    SELF_SIMULATION = "self_simulation"
    META_SELF_SIM = "meta_self_sim"
    SUPER_META = "super_meta"


class CertaintyState(str, Enum):
    """YOUKNOW's epistemic state."""
    SANCTUARY = "sanctuary"      # >0.8 - solid ground
    CAUTION = "caution"          # 0.5-0.8 - proceed carefully
    WASTELAND = "wasteland"      # <0.5 - lost coherence


# =============================================================================
# SUPERCLASS CHAIN
# =============================================================================

class SuperclassChain(BaseModel):
    """The is_a chain going upward through abstractions."""
    entity_name: str
    chain: List[str] = Field(default_factory=list)
    it_being_that: Optional[str] = None
    that_being_a_form_of: Optional[str] = None

    def extend(self, superclass: str) -> "SuperclassChain":
        """Extend chain upward."""
        new_chain = self.chain.copy()
        new_chain.append(superclass)
        return SuperclassChain(
            entity_name=self.entity_name,
            chain=new_chain,
            it_being_that=self.it_being_that,
            that_being_a_form_of=self.that_being_a_form_of
        )


# =============================================================================
# ENTITY - Base ontology unit
# =============================================================================

class Entity(BaseModel):
    """Base entity in the ontology.

    Every Entity must trace is_a to pattern_of_isa.
    """
    name: str
    description: str = ""

    # THE THREE PRIMITIVES
    is_a: List[str] = Field(default_factory=list)
    part_of: List[str] = Field(default_factory=list)
    has_parts: List[str] = Field(default_factory=list)
    produces: List[str] = Field(default_factory=list)

    python_class: Optional[str] = None
    created: datetime = Field(default_factory=datetime.now)


# =============================================================================
# PIO ENTITY - Polysemic Imaginary Ontology
# =============================================================================

class PIOEntity(Entity):
    """Entity with polysemic agentic potential.

    PIO = meanings become agentic through reification.
    is_a IS the polysemy - multiple is_a = multiple meanings.
    validation_level = how agentic (how much reified).
    """
    validation_level: ValidationLevel = ValidationLevel.EMBODIES
    self_sim_level: SelfSimulationLevel = SelfSimulationLevel.NONE
    superclass_chain: SuperclassChain = None
    raw_content: Optional[str] = None

    python_class_name: Optional[str] = None
    python_module: Optional[str] = None
    crystallized: Optional[datetime] = None
    goldenized: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.superclass_chain is None:
            self.superclass_chain = SuperclassChain(entity_name=self.name)


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
    """What YOUKNOW perceives when given any structure."""
    objects: List[str] = Field(default_factory=list)
    morphisms: List[Morphism] = Field(default_factory=list)
    has_identity: bool = False
    has_composition: bool = False
    is_functor: bool = False

    def describe(self) -> str:
        return f"""Category Structure:
  Objects: {self.objects}
  Morphisms: {[str(m) for m in self.morphisms]}
  Has identity: {self.has_identity}
  Has composition: {self.has_composition}
  Is functor: {self.is_functor}"""


# =============================================================================
# VALIDATION RESULT
# =============================================================================

class ValidationResult(BaseModel):
    """Result of validating an is_a chain."""
    valid: bool
    chain: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    message: str = ""
    certainty: float = 1.0


# =============================================================================
# UCO MODELS - Chain and Link
# =============================================================================

class LinkType(str, Enum):
    """Types of links in a chain."""
    ISA = "is_a"
    PARTOF = "part_of"
    PRODUCES = "produces"
    EMBODIES = "embodies"
    MANIFESTS = "manifests"
    REIFIES = "reifies"


class Link(BaseModel):
    """A single link in a chain."""
    source: str
    target: str
    link_type: LinkType = LinkType.ISA

    def __repr__(self):
        return f"{self.source} --{self.link_type.value}--> {self.target}"


class Chain(BaseModel):
    """A chain of links representing a trace."""
    name: str
    links: List[Link] = Field(default_factory=list)

    def add_link(self, source: str, target: str, link_type: LinkType = LinkType.ISA) -> None:
        self.links.append(Link(source=source, target=target, link_type=link_type))

    def is_complete(self) -> bool:
        """Does chain end at pattern_of_isa?"""
        if not self.links:
            return False
        return self.links[-1].target == "pattern_of_isa"

    def __repr__(self):
        if not self.links:
            return f"Chain({self.name}): empty"
        path = " -> ".join([self.links[0].source] + [l.target for l in self.links])
        return f"Chain({self.name}): {path}"


class DualLoop(BaseModel):
    """Dual loop: is_a chain + part_of chain."""
    entity_name: str
    isa_chain: Chain
    partof_chain: Chain

    def is_closed(self) -> bool:
        """Do both chains reach their roots?"""
        return self.isa_chain.is_complete() and len(self.partof_chain.links) > 0
