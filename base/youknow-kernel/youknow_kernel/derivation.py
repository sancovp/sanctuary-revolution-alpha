"""
YOUKNOW Derivation Validator

This is NOT string matching. This validates the DERIVATION CHAIN.

The pattern_of_is_a is achieved when a concept has:
1. Traced through embodies → manifests → reifies → produces → programs
2. Each step has its requirements satisfied
3. The final state is isA_pattern (Reality)

Three types of is_a:
- isA_primitive: Raw assertion (SOUP level)
- isA_promotion: Gone through EMR (becomes generative)
- isA_pattern: Matches pattern_of_is_a (is Reality)

Seven derivation steps (Core Sentence):
1. is_a_primitive (L0: String Soup)
2. embodies (L1: Named Slots) - self-identification
3. manifests (L2: Typed Slots) - containment 
4. reifies (L3: Struct Types) - pattern locked
5. is_a_promotion (L4+: Recursive) - becomes Program
6. produces (Closure) - what this concept generates
7. programs (LITERAL CODEGEN) - Cat-of-Cat witness
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class DerivationLevel(Enum):
    """The 7 levels of the derivation chain."""
    L0_STRING_SOUP = 0      # Raw is_a_primitive
    L1_NAMED_SLOTS = 1      # embodies
    L2_TYPED_SLOTS = 2      # manifests
    L3_STRUCT_TYPES = 3     # reifies
    L4_RECURSIVE = 4        # is_a_promotion
    L5_CLOSURE = 5          # produces
    L6_CODEGEN = 6          # programs (Reality)


class IsAType(Enum):
    """Three aspects of is_a."""
    PRIMITIVE = "isA_primitive"     # Raw assertion (SOUP)
    PROMOTION = "isA_promotion"     # Gone through EMR
    PATTERN = "isA_pattern"         # Matches pattern_of_is_a (Reality)


@dataclass
class DerivationState:
    """The derivation state of a concept."""
    name: str
    level: DerivationLevel = DerivationLevel.L0_STRING_SOUP
    is_a_type: IsAType = IsAType.PRIMITIVE
    
    # State flags
    has_is_a_primitive: bool = False    # L0
    has_embodies: bool = False          # L1: has stable slots
    has_manifests: bool = False         # L2: slots are typed
    has_reifies: bool = False           # L3: types have structure
    has_is_a_promotion: bool = False    # L4: promoted to Program
    has_produces: bool = False          # L5: what it generates
    has_programs: bool = False          # L6: Cat-of-Cat witness
    
    # Typed depth (how many layers are typed before soup)
    typed_depth: int = 0
    
    # What's missing for next level
    whats_missing: List[str] = field(default_factory=list)
    
    def is_soup(self) -> bool:
        """Is this still in SOUP (unvalidated)?"""
        return self.level.value < DerivationLevel.L3_STRUCT_TYPES.value
    
    def is_ont(self) -> bool:
        """Is this in ONT (validated)?"""
        return self.level.value >= DerivationLevel.L5_CLOSURE.value
    
    def is_reality(self) -> bool:
        """Has this reached Reality (Cat-of-Cat witness)?"""
        return self.has_programs


@dataclass 
class DerivationRequirements:
    """What a concept needs for each derivation level."""
    
    @staticmethod
    def for_embodies(concept: Dict) -> List[str]:
        """L1: What's needed for embodies (named slots)?"""
        missing = []
        if not concept.get("name"):
            missing.append("name: stable identifier")
        if not concept.get("is_a"):
            missing.append("is_a: at least one parent")
        if not concept.get("description"):
            missing.append("description: what it is")
        return missing
    
    @staticmethod
    def for_manifests(concept: Dict) -> List[str]:
        """L2: What's needed for manifests (typed slots)?"""
        missing = []

        # Real typing comes from is_a/part_of relationships and tracing to Cat_of_Cat
        # Not from XML Schema prefixes - removed xsd: check as over-engineering

        if not concept.get("y_layer"):
            missing.append("y_layer: which Y-strata layer")
        return missing
    
    @staticmethod
    def for_reifies(concept: Dict, cat=None) -> List[str]:
        """L3: What's needed for reifies (structured types)?

        is_a parents must themselves have typed_depth >= 1.
        This is the 2-morphism: your parents' relationships
        must also decompose into foundation predicates.
        """
        missing = []
        is_a = concept.get("is_a", [])
        if cat:
            from .universal_pattern import compute_ses_typed_depth
            typed_symbols = set(cat.entities.keys()) if cat else set()
            for parent in is_a:
                if parent in cat.entities:
                    parent_entity = cat.entities[parent]
                    parent_args = {
                        "is_a": list(parent_entity.is_a),
                        "part_of": list(parent_entity.part_of),
                        "has_part": list(parent_entity.has_part),
                        "produces": list(parent_entity.produces),
                    }
                    parent_ses = compute_ses_typed_depth(
                        constructor_name=parent,
                        constructor_args=parent_args,
                        typed_symbols=typed_symbols,
                    )
                    if parent_ses.max_typed_depth < 1:
                        missing.append(f"is_a parent '{parent}' has typed_depth={parent_ses.max_typed_depth} (need >= 1)")
        if not concept.get("part_of"):
            missing.append("part_of: where it belongs in the structure")
        return missing
    
    @staticmethod
    def for_promotion(concept: Dict, cat) -> List[str]:
        """L4: What's needed for is_a_promotion (recursive)?"""
        missing = []
        # Must trace to Cat_of_Cat
        name = concept.get("name", "")
        if cat and not cat.validate_traces_to_root(name):
            parents = concept.get("is_a", [])
            has_prospective_root = any(
                parent in getattr(cat, "entities", {}) and cat.validate_traces_to_root(parent)
                for parent in parents
            )
            if not has_prospective_root:
                missing.append("Doesn't trace to Cat_of_Cat")
        return missing
    
    @staticmethod
    def for_produces(concept: Dict) -> List[str]:
        """L5: What's needed for produces (closure)?
        
        The 'produces' predicate describes what this concept generates.
        Accepts both 'produces' and legacy 'instantiates' keys.
        """
        missing = []
        if not concept.get("produces") and not concept.get("instantiates"):
            missing.append("produces: what this concept generates")
        return missing
    
    @staticmethod
    def for_programs(concept: Dict, cat=None) -> List[str]:
        """L6: What's needed for programs (strengthened)?

        programs = the entire subgraph is typed all the way down.
        SES typed-depth covers all constructor args with no arbitrary
        strings remaining. first_arbitrary_string_depth must be None.
        """
        from .universal_pattern import compute_ses_typed_depth

        typed_symbols = set(cat.entities.keys()) if cat else set()
        constructor_args = {
            "is_a": concept.get("is_a", []),
            "part_of": concept.get("part_of", []),
            "has_part": concept.get("has_part", []),
            "produces": concept.get("produces", []),
            "justifies": concept.get("justifies") or concept.get("properties", {}).get("justifies"),
            "msc": (
                concept.get("has_msc")
                or concept.get("msc")
                or concept.get("properties", {}).get("hasMSC")
                or concept.get("properties", {}).get("msc")
            ),
        }
        report = compute_ses_typed_depth(
            constructor_name=concept.get("name", "unknown"),
            constructor_args=constructor_args,
            typed_symbols=typed_symbols,
        )
        missing = []
        if report.first_arbitrary_string_depth is not None:
            missing.append(
                f"not fully typed: arbitrary string at depth {report.first_arbitrary_string_depth} "
                f"(typed_depth={report.max_typed_depth}, args={report.arg_count_typed}/{report.arg_count_total})"
            )
        return missing


class DerivationValidator:
    """
    Validates derivation chains properly.
    
    NOT string matching. Checks actual requirements at each level.
    """
    
    def __init__(self, cat=None):
        """
        Args:
            cat: CategoryOfCategories instance (for Cat_of_Cat checks)
        """
        self.cat = cat
    
    def validate(self, concept: Dict[str, Any]) -> DerivationState:
        """
        Validate a concept's derivation state.
        
        Returns DerivationState showing:
        - Current level (L0-L6)
        - is_a type (primitive/promotion/pattern)
        - What's missing for next level
        """
        name = concept.get("name", "unknown")
        state = DerivationState(name=name)
        
        # Check each level progressively
        
        # L0: is_a_primitive (has any is_a at all)
        if concept.get("is_a"):
            state.has_is_a_primitive = True
            state.level = DerivationLevel.L0_STRING_SOUP
        
        # L1: embodies (has named slots)
        missing_l1 = DerivationRequirements.for_embodies(concept)
        if not missing_l1:
            state.has_embodies = True
            state.level = DerivationLevel.L1_NAMED_SLOTS
            state.typed_depth = 1
        else:
            state.whats_missing = missing_l1
            return state
        
        # L2: manifests (slots are typed)
        missing_l2 = DerivationRequirements.for_manifests(concept)
        if not missing_l2:
            state.has_manifests = True
            state.level = DerivationLevel.L2_TYPED_SLOTS
            state.typed_depth = 2
        else:
            state.whats_missing = missing_l2
            return state
        
        # L3: reifies (types have structure — parents must be typed)
        missing_l3 = DerivationRequirements.for_reifies(concept, self.cat)
        if not missing_l3:
            state.has_reifies = True
            state.level = DerivationLevel.L3_STRUCT_TYPES
            state.typed_depth = 3
            state.is_a_type = IsAType.PROMOTION  # Now it's promoted
        else:
            state.whats_missing = missing_l3
            return state
        
        # L4: is_a_promotion (recursive, traces to Cat_of_Cat)
        missing_l4 = DerivationRequirements.for_promotion(concept, self.cat)
        if not missing_l4:
            state.has_is_a_promotion = True
            state.level = DerivationLevel.L4_RECURSIVE
            state.typed_depth = 4
        else:
            state.whats_missing = missing_l4
            return state
        
        # L5: produces (closure — what it generates)
        missing_l5 = DerivationRequirements.for_produces(concept)
        if not missing_l5:
            state.has_produces = True
            state.level = DerivationLevel.L5_CLOSURE
            state.typed_depth = 5
        else:
            state.whats_missing = missing_l5
            return state
        
        # L6: programs (fully strengthened — SES covers all args)
        missing_l6 = DerivationRequirements.for_programs(concept, self.cat)
        if not missing_l6:
            state.has_programs = True
            state.level = DerivationLevel.L6_CODEGEN
            state.typed_depth = 6
            state.is_a_type = IsAType.PATTERN  # Now it's Reality
        else:
            state.whats_missing = missing_l6
            return state
        
        return state
    
    def validate_for_promotion(self, concept: Dict[str, Any], min_depth: int = 3) -> Dict[str, Any]:
        """
        Check if concept is ready for SOUP → ONT promotion.
        
        Requirements (from UARL v4):
        1. typed_depth >= minimum_typed_layers
        2. no_untyped_morphisms
        3. llm_satisfied (we assume True if other checks pass)
        """
        state = self.validate(concept)
        
        can_promote = state.typed_depth >= min_depth
        
        return {
            "can_promote": can_promote,
            "state": state,
            "typed_depth": state.typed_depth,
            "required_depth": min_depth,
            "whats_missing": state.whats_missing,
            "is_ont": state.is_ont(),
            "is_reality": state.is_reality(),
        }


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== DERIVATION VALIDATOR ===")
    print()
    
    validator = DerivationValidator()
    
    # Test concept at L0 (soup)
    soup_concept = {
        "name": "RawThing",
        "is_a": ["Something"],
    }
    state = validator.validate(soup_concept)
    print("1. Soup concept (minimal):")
    print(f"   Level: {state.level.name}")
    print(f"   is_a type: {state.is_a_type.value}")
    print(f"   Typed depth: {state.typed_depth}")
    print(f"   Missing: {state.whats_missing}")
    print()
    
    # Test concept at L3 (reified)
    typed_concept = {
        "name": "SkillSpec",
        "is_a": ["Category"],
        "description": "Specification for a PAIA skill",
        "y_layer": "Y3",
        "part_of": ["PAIAB_System"],
        "properties": {
            "domain": "xsd:string",
            "category": "xsd:string",
        }
    }
    state = validator.validate(typed_concept)
    print("2. Typed concept (L3):")
    print(f"   Level: {state.level.name}")
    print(f"   is_a type: {state.is_a_type.value}")
    print(f"   Typed depth: {state.typed_depth}")
    print(f"   Missing: {state.whats_missing}")
    print()
    
    # Test concept at L6 (Reality)
    reality_concept = {
        "name": "SkillSpec",
        "is_a": ["Category"],
        "description": "Specification for a PAIA skill",
        "y_layer": "Y3",
        "part_of": ["PAIAB_System"],
        "produces": ["SkillPackage"],
        "python_class": "SkillSpec",
        "properties": {
            "domain": "xsd:string",
            "category": "xsd:string",
        }
    }
    state = validator.validate(reality_concept)
    print("3. Reality concept (L6):")
    print(f"   Level: {state.level.name}")
    print(f"   is_a type: {state.is_a_type.value}")
    print(f"   Typed depth: {state.typed_depth}")
    print(f"   Is SOUP: {state.is_soup()}")
    print(f"   Is ONT: {state.is_ont()}")
    print(f"   Is Reality: {state.is_reality()}")
    print()
    
    # Test promotion check
    print("4. Promotion check (min_depth=3):")
    result = validator.validate_for_promotion(typed_concept, min_depth=3)
    print(f"   Can promote: {result['can_promote']}")
    print(f"   Typed depth: {result['typed_depth']}")
    print(f"   Missing: {result['whats_missing']}")
