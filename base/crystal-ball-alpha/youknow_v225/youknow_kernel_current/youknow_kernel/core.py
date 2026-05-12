"""YOUKNOW Core - Built on Category of Categories.

YOUKNOW IS built on Cat of Cat. Not delegating to utils.
Cat of Cat IS the foundation. Everything goes through it.

Derivation is NOT string matching. It validates:
- The 7-step chain: embodies → manifests → reifies → produces → programs
- Three is_a types: primitive, promotion, pattern
- Typed depth for SOUP → ONT promotion

Hyperedge validation:
- Validates is_a CLAIMS against hyperedge CONTEXT
- The pattern of relationships TOGETHER instantiate the is_a
- pattern_of_is_a is the WITNESS
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .owl_types import (
    CategoryOfCategories,
    CatEntity,
    PrimitiveCategory,
    PrimitiveRelationship,
    get_cat,
)

from .derivation import (
    DerivationValidator,
    DerivationState,
    DerivationLevel,
    IsAType,
)

from .hyperedge import (
    HyperedgeValidator,
    HyperedgeContext,
    ClaimValidation,
    ClaimStrength,
    validate_is_a_claim,
)

from .completeness import (
    CompletenessValidator,
    CompletenessResult,
)

# Late import to avoid circular - pipeline uses YOUKNOW internals
_PIPELINE = None

def _get_pipeline():
    """Get pipeline lazily to avoid circular import."""
    global _PIPELINE
    if _PIPELINE is None:
        from .pipeline import YouknowPipeline
        _PIPELINE = YouknowPipeline()
    return _PIPELINE


@dataclass
class YOUKNOW:
    """
    The homoiconic kernel. BUILT ON OWL type registry.

    YOUKNOW validates claims against OWL restrictions via system_type_validator
    + recursive restriction walk. Cat_of_Cat is the terminal axiom in the OWL.
    owl_types.py provides the type registry (replaces cat_of_cat.py).
    
    Derivation validation checks the 7-step chain, not string matching.
    Hyperedge validation validates is_a CLAIMS against hyperedge CONTEXT.
    Completeness validation: EVERY label must have ALL THREE (is_a, part_of, produces).
    """
    
    cat: CategoryOfCategories = field(default_factory=get_cat)
    derivation: DerivationValidator = field(default=None)
    hyperedge: HyperedgeValidator = field(default=None)
    completeness: CompletenessValidator = field(default=None)
    certainty: float = 1.0
    created: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Ensure Cat of Cat and validators are properly initialized."""
        # YOUKNOW itself must exist in the ontology
        if "YOUKNOW" not in self.cat.entities:
            raise RuntimeError("Cat of Cat not properly initialized - YOUKNOW missing")
        
        # Verify the self-loop exists
        root = self.cat.get("Cat_of_Cat")
        if not root or "Cat_of_Cat" not in root.is_a:
            raise RuntimeError("Cat of Cat self-loop broken - ontology invalid")
        
        # Initialize derivation validator with Cat of Cat
        if self.derivation is None:
            self.derivation = DerivationValidator(cat=self.cat)
        
        # Initialize hyperedge validator with Cat of Cat
        if self.hyperedge is None:
            self.hyperedge = HyperedgeValidator(cat=self.cat)
        
        # Initialize completeness validator with Cat of Cat
        if self.completeness is None:
            self.completeness = CompletenessValidator(cat=self.cat)
    
    # =========================================================================
    # ADD TO ONTOLOGY
    # =========================================================================
    
    def add(self,
            name: str,
            is_a: List[str],
            part_of: List[str] = None,
            has_part: List[str] = None,
            produces: List[str] = None,
            y_layer: str = None,
            properties: Dict[str, Any] = None,
            description: str = None,
            relationships: Dict[str, List[str]] = None,
            skip_pipeline: bool = False) -> CatEntity:
        """
        Add an entity to the ontology.

        MUST trace back to Cat_of_Cat via is_a chain.

        This is THE entry point. Internally:
        1. Does string tracking (Cat_of_Cat) - structural boundary
        2. Calls pipeline for OWL/SHACL validation - semantic validation
        3. Runs EMR processing - derivation completeness
        4. Runs PIO discovery - isomorphism detection
        5. Mirrors to Carton - search/agent layer

        Args:
            skip_pipeline: If True, only do Cat_of_Cat (for bootstrap/testing)

        Returns the created entity.
        """
        # 1. Cat_of_Cat - structural boundary tracking
        entity = self.cat.add(
            name=name,
            is_a=is_a,
            part_of=part_of or [],
            has_part=has_part or [],
            produces=produces or [],
            y_layer=y_layer,
            properties=properties or {},
            description=description or "",
        )

        # 2. Pipeline - EMR + PIO + UARL + OWL + Carton
        if not skip_pipeline:
            try:
                pipeline = _get_pipeline()
                pipeline_result = pipeline.add_concept(
                    name=name,
                    description=description or properties.get("description", "") if properties else "",
                    is_a=is_a,
                    relationships=relationships or {},
                    properties=properties or {}
                )
                # Store pipeline result on entity for access
                entity.pipeline_result = pipeline_result
            except Exception:
                # Pipeline failure should not break Cat_of_Cat
                import logging
                import traceback
                tb = traceback.format_exc()
                logging.getLogger(__name__).error(f"Pipeline error for {name}: {tb}")
                entity.pipeline_error = tb

        return entity
    
    def get(self, name: str) -> Optional[CatEntity]:
        """Get an entity from the ontology."""
        return self.cat.get(name)
    
    def exists(self, name: str) -> bool:
        """Does this entity exist in the ontology?"""
        return name in self.cat.entities
    
    # =========================================================================
    # VALIDATION - Cat of Cat (structural)
    # =========================================================================
    
    def validate(self, name: str) -> Dict[str, Any]:
        """
        Validate an entity against Cat of Cat (structural validation).
        
        Checks:
        1. Entity exists
        2. Traces back to Cat_of_Cat
        3. Y-layer is valid
        4. is_a parents exist
        5. part_of parents exist
        
        Returns dict with valid=True/False and errors list.
        """
        errors = []
        
        # 1. Exists?
        if not self.exists(name):
            return {"valid": False, "errors": [f"Entity '{name}' not in ontology"]}
        
        entity = self.get(name)
        
        # 2. Traces to root?
        if not self.cat.validate_traces_to_root(name):
            errors.append(f"Entity '{name}' does not trace back to Cat_of_Cat")
        
        # 3. is_a parents exist?
        for parent in entity.is_a:
            if parent not in self.cat.entities:
                errors.append(f"is_a parent '{parent}' does not exist")
        
        # 4. part_of parents exist?
        for parent in entity.part_of:
            if parent not in self.cat.entities:
                errors.append(f"part_of parent '{parent}' does not exist")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "trace": self.cat.trace_to_root(name),
            # Y-layer moved to SOMA (soma_y_mesh.pl 2026-04-06) — Python path deprecated.
            # "y_layer": self.cat.get_y_layer(name),
        }
    
    def is_valid(self, name: str) -> bool:
        """Quick check: is this entity valid structurally?"""
        return self.validate(name)["valid"]
    
    # =========================================================================
    # DERIVATION - The 7-step chain (NOT string matching)
    # =========================================================================
    
    def derive(self, concept: Dict[str, Any]) -> DerivationState:
        """
        Check derivation state of a concept.
        
        This is NOT string matching. It validates:
        - L0: is_a_primitive (has any is_a)
        - L1: embodies (has stable slots)
        - L2: manifests (slots are typed)
        - L3: reifies (types have structure)
        - L4: is_a_promotion (traces to Cat_of_Cat)
        - L5: produces (produces things)
        - L6: programs (Cat-of-Cat witness, codegen)
        
        Returns DerivationState with level, is_a_type, whats_missing.
        """
        return self.derivation.validate(concept)
    
    def derive_entity(self, name: str) -> DerivationState:
        """Derive the state of an entity in the ontology."""
        if not self.exists(name):
            state = DerivationState(name=name)
            state.whats_missing = [f"Entity '{name}' does not exist"]
            return state
        
        entity = self.get(name)
        concept = {
            "name": entity.name,
            "is_a": entity.is_a,
            "part_of": entity.part_of,
            "has_part": entity.has_part,
            "produces": entity.produces,
            "y_layer": entity.y_layer,
            "properties": entity.properties,
            "description": getattr(entity, 'description', None) or entity.properties.get("description", ""),
        }
        return self.derive(concept)
    
    def can_promote(self, name: str, min_depth: int = 3) -> Dict[str, Any]:
        """
        Check if entity is ready for SOUP → ONT promotion.
        
        Requirements:
        1. typed_depth >= min_depth
        2. Traces to Cat_of_Cat
        3. All required fields present
        
        Returns dict with can_promote, typed_depth, whats_missing.
        """
        if not self.exists(name):
            return {
                "can_promote": False,
                "typed_depth": 0,
                "whats_missing": [f"Entity '{name}' does not exist"],
            }
        
        entity = self.get(name)
        concept = {
            "name": entity.name,
            "is_a": entity.is_a,
            "part_of": entity.part_of,
            "has_part": entity.has_part,
            "produces": entity.produces,
            "y_layer": entity.y_layer,
            "properties": entity.properties,
            "description": entity.properties.get("description", ""),
        }
        return self.derivation.validate_for_promotion(concept, min_depth)
    
    def is_soup(self, name: str) -> bool:
        """Is this entity still in SOUP (unvalidated)?"""
        state = self.derive_entity(name)
        return state.is_soup()
    
    def is_ont(self, name: str) -> bool:
        """Is this entity in ONT (validated)?"""
        state = self.derive_entity(name)
        return state.is_ont()
    
    def is_reality(self, name: str) -> bool:
        """Has this entity reached Reality (Cat-of-Cat witness)?"""
        state = self.derive_entity(name)
        return state.is_reality()
    
    # =========================================================================
    # CLAIM VALIDATION - Hyperedge pattern_of_is_a
    # =========================================================================
    
    def validate_claim(self, subject: str, object_: str) -> ClaimValidation:
        """
        Validate the claim: "subject is_a object_"
        
        This validates is_a CLAIMS against hyperedge CONTEXT.
        The pattern of relationships TOGETHER instantiate the is_a.
        
        Returns ClaimValidation with:
        - valid: bool
        - strength: ClaimStrength
        - witness: The pattern_of_is_a witness
        - supporting_evidence, missing_evidence
        
        Example:
            result = yk.validate_claim("SkillSpec", "Category")
            print(result.explain())
        """
        return self.hyperedge.validate_claim(subject, object_)
    
    def is_a_witnessed(self, subject: str, object_: str) -> bool:
        """
        Is the claim "subject is_a object_" witnessed by pattern_of_is_a?
        
        Returns True only if the claim is WITNESSED (full pattern support).
        """
        result = self.validate_claim(subject, object_)
        return result.strength == ClaimStrength.WITNESSED
    
    def is_a_supported(self, subject: str, object_: str) -> bool:
        """
        Is the claim "subject is_a object_" supported by hyperedge context?
        
        Returns True if valid (any strength).
        """
        result = self.validate_claim(subject, object_)
        return result.valid
    
    def explain_claim(self, subject: str, object_: str) -> str:
        """
        Explain why the claim "subject is_a object_" is valid/invalid.
        
        Returns human-readable explanation.
        """
        result = self.validate_claim(subject, object_)
        return result.explain()
    
    # =========================================================================
    # COMPLETENESS - EVERY label must have ALL THREE
    # =========================================================================
    
    def check_complete(self, name: str) -> CompletenessResult:
        """
        Check if a label has the complete triplet.
        
        EVERY label must have:
        - is_a (traces to Cat_of_Cat)
        - part_of (traces to Cat_of_Cat)
        - instantiates (traces to Cat_of_Cat)
        
        Recursively checks all targets.
        
        Returns CompletenessResult with explain() method.
        """
        self.completeness._cache = {}  # Clear cache for fresh check
        return self.completeness.check(name)
    
    def is_complete(self, name: str) -> bool:
        """Quick check: does this entity have the complete triplet?"""
        result = self.check_complete(name)
        return result.complete
    
    def explain_completeness(self, name: str) -> str:
        """Explain what's missing for completeness."""
        result = self.check_complete(name)
        return result.explain()
    
    def get_incomplete(self) -> List[str]:
        """Get all incomplete entities in the ontology."""
        self.completeness._cache = {}
        return self.completeness.get_incomplete()
    
    def get_missing_triplets(self) -> Dict[str, List[str]]:
        """Get what each entity is missing (is_a, part_of, produces)."""
        self.completeness._cache = {}
        return self.completeness.get_missing_triplets()
    
    # =========================================================================
    # QUERIES
    # =========================================================================
    
    def trace(self, name: str) -> List[str]:
        """Trace is_a chain back to Cat_of_Cat."""
        return self.cat.trace_to_root(name)
    
    def y_layer(self, name: str) -> Optional[str]:
        """What Y-layer is this entity in?"""
        # Y-layer moved to SOMA (soma_y_mesh.pl 2026-04-06) — Python path deprecated.
        # return self.cat.get_y_layer(name)
        return None

    def list_layer(self, layer: str) -> List[str]:
        """List all entities in a Y-layer."""
        # Y-layer moved to SOMA (soma_y_mesh.pl 2026-04-06) — Python path deprecated.
        # return self.cat.list_by_layer(layer)
        return []
    
    def is_a(self, child: str, parent: str) -> bool:
        """Does child is_a parent (directly)?"""
        entity = self.get(child)
        if not entity:
            return False
        return parent in entity.is_a
    
    def is_a_transitive(self, child: str, ancestor: str) -> bool:
        """Does child is_a ancestor (transitively)?"""
        chain = self.trace(child)
        return ancestor in chain
    
    def part_of(self, part: str, whole: str) -> bool:
        """Is part part_of whole (directly)?"""
        entity = self.get(part)
        if not entity:
            return False
        return whole in entity.part_of
    
    def has_part(self, whole: str, part: str) -> bool:
        """Does whole has_part part (directly)?"""
        entity = self.get(whole)
        if not entity:
            return False
        return part in entity.has_part
    
    # =========================================================================
    # THE CORE QUESTION: WHAT IS X?
    # =========================================================================
    
    def what_is(self, name: str) -> str:
        """
        Answer: What is X?
        
        This is YOUKNOW's primary function.
        Returns a sentence describing the entity's position in the ontology.
        """
        if not self.exists(name):
            return f"{name} is not in the ontology."
        
        entity = self.get(name)
        trace = self.trace(name)
        y = self.y_layer(name)
        
        lines = []
        
        # is_a chain
        if trace:
            lines.append(f"{name} IS_A {' → '.join(trace[1:])}")
        
        # part_of
        if entity.part_of:
            lines.append(f"{name} PART_OF {', '.join(entity.part_of)}")
        
        # has_part
        if entity.has_part:
            lines.append(f"{name} HAS_PART {', '.join(entity.has_part)}")
        
        # produces
        if entity.produces:
            lines.append(f"{name} PRODUCES {', '.join(entity.produces)}")
        
        # Y-layer
        if y:
            lines.append(f"Y-LAYER: {y}")
        
        # Description
        desc = entity.properties.get("description", "")
        if desc:
            lines.append(f"DESCRIPTION: {desc}")
        
        return "\n".join(lines) if lines else f"{name} exists but has no relationships."
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Get ontology statistics."""
        return self.cat.stats()
    
    def __repr__(self) -> str:
        stats = self.stats()
        return f"YOUKNOW(entities={stats['total_entities']}, layers={stats['by_layer']})"


# =============================================================================
# FACTORY
# =============================================================================

_GLOBAL_YOUKNOW: Optional[YOUKNOW] = None

def get_youknow() -> YOUKNOW:
    """Get the global YOUKNOW instance."""
    global _GLOBAL_YOUKNOW
    if _GLOBAL_YOUKNOW is None:
        _GLOBAL_YOUKNOW = YOUKNOW()
    return _GLOBAL_YOUKNOW

def reset_youknow():
    """Reset YOUKNOW (for testing)."""
    global _GLOBAL_YOUKNOW
    _GLOBAL_YOUKNOW = None


# For compatibility with old code
def create_root_entities():
    """Deprecated. Cat of Cat auto-initializes."""
    return get_youknow()


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== YOUKNOW BUILT ON CAT OF CAT ===")
    print()
    
    yk = get_youknow()
    
    print("1. YOUKNOW initialized:")
    print(f"   {yk}")
    print()
    
    print("2. What is Entity?")
    print(yk.what_is("Entity"))
    print()
    
    print("3. What is Pattern?")
    print(yk.what_is("Pattern"))
    print()
    
    print("4. What is YOUKNOW?")
    print(yk.what_is("YOUKNOW"))
    print()
    
    print("5. Add a new entity:")
    yk.add(
        "SkillSpec",
        is_a=["Category"],
        part_of=["YOUKNOW"],
        produces=["SkillPackage"],
        y_layer="Y3",
        properties={"description": "Specification for a PAIA skill."}
    )
    print(yk.what_is("SkillSpec"))
    print()
    
    print("6. Validate SkillSpec:")
    result = yk.validate("SkillSpec")
    print(f"   Valid: {result['valid']}")
    print(f"   Trace: {result['trace']}")
    print(f"   Y-layer: {result['y_layer']}")
    print()
    
    print("7. Is SkillSpec is_a Entity (transitive)?")
    print(f"   {yk.is_a_transitive('SkillSpec', 'Entity')}")
    print()
    
    print("8. Stats:")
    print(f"   {yk.stats()}")
