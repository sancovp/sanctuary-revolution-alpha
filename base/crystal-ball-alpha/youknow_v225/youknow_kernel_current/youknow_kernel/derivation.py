"""
YOUKNOW Derivation Validator

!! THIS IS THE PROMPTING HARNESS, NOT A ONE-SHOT VALIDATOR !!

The derivation chain is walked ONLY when a concept is INCOMPLETE (SOUP).
Complete concepts that hit known ONT types skip this entirely.

Each level tells the LLM what to provide next:
  L0: "You said X is_a Y. OK, now where does it live?" → need part_of
  L1: "Good, part_of Z. Now what does it produce?" → need produces
  L2: "OK, produces W. Let me check chain closure..." → CatOfCat trace
  L3: "Chain closes. Do your targets also close?" → recursive check
  L5: "Y-strata filled?" → programs threshold
  L6: "Everything fully typed?" → ONT admission

The compiler calls youknow() REPEATEDLY. Each call returns SOUP with
what's missing. The LLM reads that and provides it. Progressive.

!! CURRENT STATE (2026-04-19) !!

SUPPLEMENTARY to the main validation path. The compiler now uses:
  1. system_type_validator (CODE gate for system types — reads OWL restrictions)
  2. Recursive restriction walk (checks all restrictions recursively, instant)
  3. reifies as deduction chain terminal

This derivation validator provides L0-L6 progressive levels as diagnostic
info and EMR state tracking. It is NOT the primary admission gate.
The CODE gate is system_type_validator. The SOUP errors come from the walk.

GOAL: Port to SOMA/Prolog for ONT layer (recursive core sentence check).

Validates the DERIVATION CHAIN for a label's subgraph.

A label (e.g., "Dog") is NOT a physical thing. It IS a bundle of claims (EMR)
that, when reified, produce a PatternOfIsA subgraph that programs the label
into existence as a valid ontological entity.

The chain:
1. User says "Dog is_a Animal" → candidate/primitive_is_a claim → SOUP
2. More claims accumulate under the label (part_of, produces, etc.)
3. Those claims form a SUBGRAPH under the label
4. When the subgraph has enough structure → justifies MSC of PatternOfIsA
5. PatternOfIsA gets codegen → programs relationship
6. Admitted to ONT

EMR (the epistemic states of any claim):
  E (Embodies) = ANY is_a claim exists. Every claim starts here.
  M (Manifests) = Disambiguating WHY and HOW. Relationships typed.
  R (Reifies)   = ADMITTED. Chain closes. Is_a(Reality).

Y-Strata completion (what PROGRAMS means):
  A label is PROGRAMS when at least Y2+Y3+Y4+Y5 are filled:
    Y2: Universal class declared (is_a pointing to a known class)
    Y3: Process defined (produces — what it generates/does)
    Y4: Specific instance exists (something is_a THIS label)
    Y5: Generator defined (something that produces instances of this)
  Y1 is foundation (a priori). Y6 is optional specialization.

Boundedness:
  ONT does NOT mean "complete forever." ONT means "bounded enough to generate
  FROM THIS VIEW." The ontology of Dog is infinite. But if you have enough
  Y-layers that you can GENERATE dogs → bounded → programs → Reality.

Core sentence (from IJEGU):
  "from reality and is(reality): isa embodies partof manifests instantiates
   then reifies instantiates is_a programs instantiates partof reality"
  → is_a pattern_of(is_a) — the quine closure.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum


class DerivationLevel(Enum):
    """The levels of the derivation chain."""
    L0_STRING_SOUP = 0      # Raw candidate/primitive_is_a claim
    L1_NAMED_SLOTS = 1      # embodies: claim has is_a + part_of (bears containment)
    L2_TYPED_SLOTS = 2      # manifests: has produces/instantiates (pattern recognition)
    L3_STRUCT_TYPES = 3     # reifies: is_a chain closes to Cat_of_Cat
    L4_RECURSIVE = 4        # is_a_promotion: relationship targets also have closed chains
    L5_CLOSURE = 5          # Y-strata filled: at least Y2+Y3+Y4+Y5
    L6_CODEGEN = 6          # programs: all relationship targets also have derivation chains


class IsAType(Enum):
    """Three aspects of is_a."""
    PRIMITIVE = "isA_primitive"     # Raw assertion (SOUP)
    PROMOTION = "isA_promotion"     # Gone through EMR, chain closes
    PATTERN = "isA_pattern"         # Matches pattern_of_is_a (Reality)


@dataclass
class DerivationState:
    """The derivation state of a concept's label subgraph."""
    name: str
    level: DerivationLevel = DerivationLevel.L0_STRING_SOUP
    is_a_type: IsAType = IsAType.PRIMITIVE

    # State flags — each corresponds to a level
    has_is_a_primitive: bool = False    # L0: any is_a claim exists
    has_embodies: bool = False          # L1: is_a + part_of (bears containment)
    has_manifests: bool = False         # L2: produces/instantiates (pattern recognition)
    has_reifies: bool = False           # L3: is_a chain closes to Cat_of_Cat
    has_is_a_promotion: bool = False    # L4: relationship targets also close
    has_produces: bool = False          # L5: Y-strata filled (Y2+Y3+Y4+Y5)
    has_programs: bool = False          # L6: fully recursive — all targets have chains

    # How many levels are satisfied
    typed_depth: int = 0

    # What's missing for next level
    whats_missing: List[str] = field(default_factory=list)

    # Y-strata presence (deduced from what's declared)
    y_strata_present: Dict[str, bool] = field(default_factory=lambda: {
        "Y2": False, "Y3": False, "Y4": False, "Y5": False,
    })

    def is_soup(self) -> bool:
        """Is this still in SOUP (chain not closed)?"""
        return self.level.value < DerivationLevel.L3_STRUCT_TYPES.value

    def is_ont(self) -> bool:
        """Is this in ONT (Y-strata filled)?"""
        return self.level.value >= DerivationLevel.L5_CLOSURE.value

    def is_reality(self) -> bool:
        """Has this reached Reality (fully recursive programs)?"""
        return self.has_programs


@dataclass
class DerivationRequirements:
    """What a concept needs for each derivation level.

    Each method checks the ACTUAL requirement for that level,
    not just whether a dict key exists.
    """

    @staticmethod
    def for_primitive_isa(concept: Dict) -> List[str]:
        """L0: Is there any is_a claim at all?

        The label has at least one is_a assertion. This is the
        candidate/primitive_is_a. It means: someone CLAIMED this.
        The claim itself is the entity entering SOUP.
        """
        missing = []
        if not concept.get("is_a"):
            missing.append("is_a: no claim exists — need at least one is_a assertion")
        return missing

    @staticmethod
    def for_embodies(concept: Dict) -> List[str]:
        """L1: Does the claim bear containment?

        Core sentence: "isa embodies partof"
        The primitive is_a BEARS the property of containment (part_of).
        Embodies = the claim has both is_a AND part_of.
        Without part_of, the claim floats — it doesn't belong anywhere.
        """
        missing = []
        if not concept.get("is_a"):
            missing.append("is_a: at least one parent (the claim itself)")
        if not concept.get("part_of"):
            missing.append("part_of: where this belongs (containment)")
        return missing

    @staticmethod
    def for_manifests(concept: Dict) -> List[str]:
        """L2: Pattern recognition — what does this produce?

        Core sentence: "manifests instantiates"
        Manifests = you know what this thing PRODUCES or INSTANTIATES.
        This is the pattern recognition step: you can see the shape
        of what this label generates.
        """
        missing = []
        has_produces = bool(concept.get("produces"))
        has_instantiates = bool(concept.get("instantiates"))
        if not has_produces and not has_instantiates:
            missing.append("produces/instantiates: what this label generates (pattern recognition)")
        return missing

    @staticmethod
    def for_reifies(concept: Dict, cat=None) -> List[str]:
        """L3: Formal commitment — is_a chain closes to Cat_of_Cat.

        Core sentence: "reifies instantiates"
        Reification = the chain is real, not hypothetical.
        The is_a chain must trace all the way to Cat_of_Cat.
        Every is_a parent must exist in the ontology.
        """
        missing = []
        name = concept.get("name", "")

        if cat is None:
            missing.append("Cat_of_Cat not available for chain validation")
            return missing

        # Check: all is_a parents exist in the ontology
        for parent in concept.get("is_a", []):
            if parent not in cat.entities:
                missing.append(f"is_a parent '{parent}' does not exist in ontology")

        # Check: is_a chain traces to Cat_of_Cat
        # If entity is already in cat, check directly
        # If not, check if its parents trace to root
        if name in cat.entities:
            if not cat.validate_traces_to_root(name):
                missing.append(f"is_a chain for '{name}' does not reach Cat_of_Cat")
        else:
            # Entity not yet in cat — check if parents trace to root
            parents = concept.get("is_a", [])
            has_rooted_parent = any(
                parent in cat.entities and cat.validate_traces_to_root(parent)
                for parent in parents
            )
            if not has_rooted_parent:
                missing.append(f"no is_a parent traces to Cat_of_Cat — chain cannot close")

        # Check: all part_of targets exist
        for target in concept.get("part_of", []):
            if target not in cat.entities:
                missing.append(f"part_of target '{target}' does not exist in ontology")

        return missing

    @staticmethod
    def for_promotion(concept: Dict, cat=None) -> List[str]:
        """L4: Recursive — relationship targets also have closed chains.

        is_a_promotion means: not just YOUR chain closes, but the things
        you POINT TO also have closed chains. Your is_a parents are real.
        Your part_of targets are real. Your produces targets are real.

        This is the 2-morphism: your relationships' targets are themselves
        validated, not just arbitrary strings.
        """
        missing = []
        if cat is None:
            return missing

        # Check all structural relationship targets exist and trace to root
        for rel_type in ("is_a", "part_of", "produces"):
            for target in concept.get(rel_type, []):
                if target not in cat.entities:
                    missing.append(f"{rel_type} target '{target}' not in ontology")
                elif not cat.validate_traces_to_root(target):
                    missing.append(f"{rel_type} target '{target}' does not trace to Cat_of_Cat")

        return missing

    @staticmethod
    def for_y_strata(concept: Dict, cat=None) -> tuple:
        """L5: Y-strata completion — at least Y2+Y3+Y4+Y5 filled.

        PROGRAMS means the label has a complete enough ontology stack
        that you can GENERATE from it. This is bounded, not infinite.

        Y-strata are DEDUCED from what's declared:
          Y2: is_a points to a known universal class → domain declared
          Y3: produces is defined → process/application exists
          Y4: something in the ontology is_a THIS label → specific instance exists
          Y5: something produces instances of this → generator exists

        Returns (missing_list, y_strata_dict)
        """
        missing = []
        name = concept.get("name", "")
        y_strata = {"Y2": False, "Y3": False, "Y4": False, "Y5": False}

        # Y2: Universal class declared — is_a points to a known entity
        is_a = concept.get("is_a", [])
        if is_a:
            if cat and any(parent in cat.entities for parent in is_a):
                y_strata["Y2"] = True
            elif is_a:
                # Parents exist as strings but not in cat — still Y2 candidate
                y_strata["Y2"] = True  # Claim exists, even if unresolved
        if not y_strata["Y2"]:
            missing.append("Y2 (domain): no is_a pointing to known universal class")

        # Y3: Process defined — has produces
        if concept.get("produces") or concept.get("instantiates"):
            y_strata["Y3"] = True
        else:
            missing.append("Y3 (process): no produces/instantiates defined")

        # Y4: Specific instance exists — something in ontology is_a this label
        if cat and name:
            has_instance = any(
                name in entity.is_a
                for entity in cat.entities.values()
                if entity.name != name
            )
            if has_instance:
                y_strata["Y4"] = True
            else:
                missing.append(f"Y4 (instance): nothing in ontology is_a '{name}'")
        else:
            missing.append("Y4 (instance): cannot check without Cat_of_Cat")

        # Y5: Generator exists — something produces instances of this
        if cat and name:
            has_generator = any(
                name in entity.produces
                for entity in cat.entities.values()
                if entity.name != name
            )
            if has_generator:
                y_strata["Y5"] = True
            else:
                missing.append(f"Y5 (generator): nothing produces '{name}'")
        else:
            missing.append("Y5 (generator): cannot check without Cat_of_Cat")

        return missing, y_strata

    @staticmethod
    def for_programs(concept: Dict, cat=None) -> List[str]:
        """L6: Fully recursive — all relationship targets have their own chains.

        Programs = the entire subgraph under this label is typed.
        Every relationship target has its own derivation chain that
        reaches at least L3 (reifies — chain closes).

        This is the SES typed-depth check: how deep can you drill
        into the constructor args before hitting arbitrary strings?
        If first_arbitrary_string_depth is None → fully typed → programs.
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
        # Include ALL relationships from properties for recursive resolution
        # Any has_* or other predicate stored by the open parser
        props = concept.get("properties", {})
        _skip = {"hasMSC", "msc", "justifies", "justifiesEdge", "python_class",
                 "template", "compressionMode", "sesTypedDepth", "reason",
                 "intuition", "compareFrom", "mapsTo", "analogicalPattern",
                 "y_layer", "description", "loaded_from", "rdf_type",
                 "primitive", "self_referential", "self_describing"}
        for key, val in props.items():
            if key in _skip or key in constructor_args:
                continue
            if isinstance(val, list):
                constructor_args[key] = val
            elif isinstance(val, str) and val not in ("", "None"):
                constructor_args[key] = [val]
        report = compute_ses_typed_depth(
            constructor_name=concept.get("name", "unknown"),
            constructor_args=constructor_args,
            typed_symbols=typed_symbols,
        )
        missing = []
        if report.first_arbitrary_string_depth is not None:
            missing.append(
                f"not fully typed: arbitrary string at depth {report.first_arbitrary_string_depth} "
                f"(typed_depth={report.max_typed_depth}, "
                f"args={report.arg_count_typed}/{report.arg_count_total})"
            )
        return missing


class DerivationValidator:
    """Validates derivation chains for label subgraphs.

    A label is a bundle of claims (EMR). This validator checks
    whether the bundle has enough structure to form a PatternOfIsA
    that programs the label into ONT.

    The check is progressive: L0 → L1 → L2 → L3 → L4 → L5 → L6.
    Each level builds on the previous. If any level fails, the label
    stays in SOUP with explicit missingness at that level.

    READ uarl.owl BEFORE MODIFYING THIS FILE.
    """

    def __init__(self, cat=None):
        """
        Args:
            cat: CategoryOfCategories instance (for chain/ontology checks)
        """
        self.cat = cat

    def validate(self, concept: Dict[str, Any]) -> DerivationState:
        """Validate a label's derivation state.

        Walks the derivation chain progressively:
          L0: primitive_is_a — any is_a claim exists (candidate)
          L1: embodies — is_a + part_of (claim bears containment)
          L2: manifests — has produces (pattern recognition)
          L3: reifies — is_a chain closes to Cat_of_Cat
          L4: is_a_promotion — relationship targets also close
          L5: Y-strata — at least Y2+Y3+Y4+Y5 filled (programs)
          L6: programs — all targets have their own derivation chains

        Returns DerivationState with level reached and what's missing.
        """
        name = concept.get("name", "unknown")
        state = DerivationState(name=name)

        # L0: primitive_is_a — does the claim exist at all?
        missing_l0 = DerivationRequirements.for_primitive_isa(concept)
        if missing_l0:
            state.whats_missing = missing_l0
            return state
        state.has_is_a_primitive = True
        state.level = DerivationLevel.L0_STRING_SOUP

        # L1: embodies — is_a + part_of (bears containment)
        missing_l1 = DerivationRequirements.for_embodies(concept)
        if missing_l1:
            state.whats_missing = missing_l1
            return state
        state.has_embodies = True
        state.level = DerivationLevel.L1_NAMED_SLOTS
        state.typed_depth = 1

        # L2: manifests — has produces (pattern recognition)
        missing_l2 = DerivationRequirements.for_manifests(concept)
        if missing_l2:
            state.whats_missing = missing_l2
            return state
        state.has_manifests = True
        state.level = DerivationLevel.L2_TYPED_SLOTS
        state.typed_depth = 2

        # L3: reifies — is_a chain closes to Cat_of_Cat
        missing_l3 = DerivationRequirements.for_reifies(concept, self.cat)
        if missing_l3:
            state.whats_missing = missing_l3
            return state
        state.has_reifies = True
        state.level = DerivationLevel.L3_STRUCT_TYPES
        state.typed_depth = 3
        state.is_a_type = IsAType.PROMOTION

        # L4: is_a_promotion — relationship targets also have closed chains
        missing_l4 = DerivationRequirements.for_promotion(concept, self.cat)
        if missing_l4:
            state.whats_missing = missing_l4
            return state
        state.has_is_a_promotion = True
        state.level = DerivationLevel.L4_RECURSIVE
        state.typed_depth = 4

        # L5: Y-strata completion — at least Y2+Y3+Y4+Y5
        missing_l5, y_strata = DerivationRequirements.for_y_strata(concept, self.cat)
        state.y_strata_present = y_strata
        if missing_l5:
            state.whats_missing = missing_l5
            # Still set has_produces if produces exists (partial credit)
            if concept.get("produces") or concept.get("instantiates"):
                state.has_produces = True
            return state
        state.has_produces = True
        state.level = DerivationLevel.L5_CLOSURE
        state.typed_depth = 5

        # L6: programs — all targets fully typed (SES no arbitrary strings)
        missing_l6 = DerivationRequirements.for_programs(concept, self.cat)
        if missing_l6:
            state.whats_missing = missing_l6
            return state
        state.has_programs = True
        state.level = DerivationLevel.L6_CODEGEN
        state.typed_depth = 6
        state.is_a_type = IsAType.PATTERN  # Now it's Reality

        return state

    def validate_for_promotion(self, concept: Dict[str, Any], min_depth: int = 3) -> Dict[str, Any]:
        """Check if concept is ready for SOUP → ONT promotion.

        Requirements:
        1. typed_depth >= min_depth
        2. Chain closes (at least L3)
        3. Y-strata filled (at least L5 for full programs)
        """
        state = self.validate(concept)

        can_promote = state.typed_depth >= min_depth

        return {
            "can_promote": can_promote,
            "state": state,
            "typed_depth": state.typed_depth,
            "required_depth": min_depth,
            "whats_missing": state.whats_missing,
            "y_strata": state.y_strata_present,
            "is_ont": state.is_ont(),
            "is_reality": state.is_reality(),
        }
