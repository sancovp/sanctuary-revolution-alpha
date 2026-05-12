"""
Griess Constructor — A Compiler for Guarded State Machines

═══════════════════════════════════════════════════════════════

WHAT THIS IS:

A compiler that takes a declared target automorphism group (κ_user)
and outputs a guarded state machine whose correctness criterion is:
"preserve κ_user under the relevant symmetry action(s)."

When iterated (SES+1), it becomes a meta-compiler that compiles
instruction-sets-for-instruction-sets. This is the Futamura tower
applied to product construction.

═══════════════════════════════════════════════════════════════

THE UNIVERSAL INSTRUCTION SET:

The Griess construction works the same way the Monster group was
actually discovered:

  1. DECLARE the target: "there should be a group with these properties"
     (Conway & Norton, 1979 — the Moonshine conjecture)

  2. BUILD the algebra that would have that group as its automorphisms
     (Griess, 1982 — constructed the 196,884-dimensional algebra)

  3. VERIFY that Aut(algebra) = declared target
     (Borcherds, 1992 — proved it)

This is NOT: explore algebras → see what Aut groups fall out.
This IS: target Aut → construct algebra → verify Aut matches.

═══════════════════════════════════════════════════════════════

THE DUAL (Forward + Reverse):

  FORWARD (Founder mode — making domains):
    DERIVE → COMPUTE → BUILD → VERIFY → ONT
    Input: κ_user (what must be preserved for users)
    Output: a domain (algebra) whose Aut = κ_user

  REVERSE (User mode — filling domains):
    Given a domain → fill slots → lock → verify
    Input: a domain with constraints
    Output: content that satisfies those constraints

  The forward pass MUST run first. Without it, the reverse pass
  has no constraint boundary and expands indefinitely.

  This is why: if you keep building (adding equipment to a gym
  that already minSAT on equipment), you're stuck in BUILD.
  The state machine says the next state is VERIFY, not more BUILD.

═══════════════════════════════════════════════════════════════

CB MAPPING:

  Griess Phase  →  CB Operation  →  What happens
  ──────────────────────────────────────────────
  DERIVE        →  create         →  Declare the space (target κ_user)
  COMPUTE       →  bloom          →  Slots appear (what must exist)
  BUILD         →  fill           →  Content fills slots (LLM + human)
  VERIFY        →  lock + mine    →  Measure + check Aut
  ONT           →  reify          →  Admitted: T operator → next level
  SOUP          →  unlock/refill  →  Aut failed: back to fill with feedback

  SES+1 (IMPLEMENT → DERIVE) = reify → bloom at next tower level

═══════════════════════════════════════════════════════════════

FUTAMURA TOWER:

  Level 0: Compiler      → takes κ_user    → outputs product (one state machine)
  Level 1: Meta-compiler → takes κ_domain  → outputs compilers (product factories)
  Level 2: Meta²-compiler→ takes κ_meta    → outputs meta-compilers
  Crown:   Fixed point    → the instruction set that compiles itself

  Crowning = Ш = 0 + lift conditions satisfied = Monster-valid fixed point.

═══════════════════════════════════════════════════════════════

UNITARITY (the three invariants between measurements):

  U1 (Semantic):   |Ш| does not increase. No A-E violations.
                   → Already enforced by catastrophe detection in CB.

  U2 (Reversible): Everything navigable, nothing destroyed except at lock.
                   → Already enforced by CB's immutable coordinates.

  U3 (Geometric):  YOUKNOW propagates corrections through the ontology.
                   When corrections flow back, they act on the Gram matrix
                   as clean group elements (Q⊤KQ, Q ∈ Aut(ontology)).
                   → This is the empirical test that the space is correct.

═══════════════════════════════════════════════════════════════
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# PHASE DEFINITIONS
# ═══════════════════════════════════════════════════════════════

class GriessPhase(str, Enum):
    """The phases of the Griess construction.

    These are compiler passes, not project management stages.
    Each phase has a specific mathematical role:
      DERIVE:  What must be true IF it exists (declare target Aut)
      COMPUTE: What it must DO before it exists (derive constraints)
      BUILD:   The minimal space constraints force (construct algebra)
      VERIFY:  Is Aut(what you built) = the thing? (check fixed point)
    """

    # Core construction (Y1-Y4) — the compiler passes
    DERIVE = "derive"      # Y1: Declare κ_user. What must be preserved.
    COMPUTE = "compute"    # Y2: Derive what the algebra must contain.
    BUILD = "build"        # Y3: Construct the minimal algebra.
    VERIFY = "verify"      # Y4: Is Aut(algebra) = declared κ_user?

    # Meta-compilation (Y5-Y6) — the Futamura iteration
    PATTERN = "pattern"       # Y5: Class emerging from verified instances.
    IMPLEMENT = "implement"   # Y6: Implementation of pattern. SES+1 ready.

    # Terminal states
    ONT = "ont"    # Aut closes → admitted to ontology. Ship it.
    SOUP = "soup"  # Aut fails → chain breaks. SOUP tells you WHY.


# Phase → Y-layer mapping
PHASE_TO_Y = {
    GriessPhase.DERIVE: "Y1",
    GriessPhase.COMPUTE: "Y2",
    GriessPhase.BUILD: "Y3",
    GriessPhase.VERIFY: "Y4",
    GriessPhase.PATTERN: "Y5",
    GriessPhase.IMPLEMENT: "Y6",
}

# EMR state → Griess phase mapping
EMR_TO_PHASE = {
    "embodies": GriessPhase.DERIVE,
    "manifests": GriessPhase.COMPUTE,
    "reifies": GriessPhase.BUILD,
    "programs": GriessPhase.VERIFY,
}


# ═══════════════════════════════════════════════════════════════
# TRANSITION RULES — The State Machine
#
# Each phase has ONE valid next phase (forward) plus failure.
# This is not a suggestion. The state machine FORCES transitions.
# You cannot go BUILD → BUILD. The only exit from BUILD is VERIFY.
#
# This is the formal reason you must VERIFY before building more:
# the instruction set does not have a BUILD → BUILD transition.
# ═══════════════════════════════════════════════════════════════

TRANSITIONS: Dict[GriessPhase, List[GriessPhase]] = {
    GriessPhase.DERIVE: [GriessPhase.COMPUTE],
    GriessPhase.COMPUTE: [GriessPhase.BUILD],
    GriessPhase.BUILD: [GriessPhase.VERIFY],
    GriessPhase.VERIFY: [GriessPhase.ONT, GriessPhase.SOUP],
    GriessPhase.ONT: [GriessPhase.PATTERN],
    GriessPhase.PATTERN: [GriessPhase.IMPLEMENT],
    GriessPhase.IMPLEMENT: [GriessPhase.DERIVE],  # SES+1: next Futamura level
    GriessPhase.SOUP: [GriessPhase.DERIVE],        # Retry with what you learned
}

# Transition conditions — what must be true to advance
TRANSITION_CONDITIONS: Dict[str, str] = {
    "derive→compute": "κ_user declared: target Aut group named with invariants",
    "compute→build": "constraints derived: what the algebra must contain",
    "build→verify": "algebra constructed: minimal space that could have target Aut",
    "verify→ont": "Aut closes: Aut(algebra) = κ_user. Ship it.",
    "verify→soup": "Aut fails: which invariant broke? (classes A-E)",
    "ont→pattern": "enough verified instances to form a class",
    "pattern→implement": "pattern has implementation (meta-compilable)",
    "implement→derive": "SES+1: meta-compiled, restart at next Futamura level",
    "soup→derive": "retry: fix what VERIFY told you was wrong",
}


# ═══════════════════════════════════════════════════════════════
# κ_user — THE TARGET AUTOMORPHISM GROUP
#
# This is the INPUT to the compiler. Without it, VERIFY has nothing
# to check against. This is what you get from customer interviews,
# domain analysis, user research.
#
# κ_user is a set of INVARIANTS: things that must be preserved
# under all valid transformations of the product.
#
# Example (gym):
#   κ_user = {
#     "members_get_stronger": True,
#     "accessible_schedule": True,
#     "equipment_per_body_part": True,
#     "community_feel": True,
#   }
#
# The product can change in any way that preserves these invariants.
# That set of valid changes IS the automorphism group.
# ═══════════════════════════════════════════════════════════════

@dataclass
class KappaUser:
    """The target automorphism group — declared user invariants.

    These are the things that MUST be preserved under any valid
    transformation of the product. Everything else can change.

    The compiler's job is to construct an algebra (product) whose
    Aut group preserves exactly these invariants.
    """
    domain: str                          # What domain this κ is for
    invariants: Dict[str, str] = field(default_factory=dict)
    # invariant_name → description of what must be preserved
    # e.g. {"data_ownership": "user owns their data, can export anytime"}

    # TODO: invariant WEIGHTS — which invariants matter most?
    # TODO: invariant TESTS — how do you CHECK each invariant?
    #       This is where YOUKNOW validation plugs in:
    #       each invariant becomes a UARL claim that can be verified.

    # TODO: invariant COMPOSITION — when two κ_user combine,
    #       what's the product κ? This is the Griess PRODUCT RULE:
    #       κ_A ⊗ κ_B = the joint invariant set.
    #       The Aut group of the product must preserve BOTH.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "invariants": self.invariants,
        }


# ═══════════════════════════════════════════════════════════════
# CONCEPT STATE — tracking position in the construction
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConceptState:
    """Tracks a concept's position in the Griess construction."""
    name: str
    phase: GriessPhase = GriessPhase.DERIVE
    ses_depth: int = 0  # How many VERIFY→PATTERN→IMPLEMENT cycles completed
    history: List[str] = field(default_factory=list)

    # The declared target — what Aut group are we building toward?
    kappa: Optional[KappaUser] = None

    # TODO: CB binding — link to the CB space that implements this concept
    # cb_space_name: Optional[str] = None
    # cb_kernel_id: Optional[int] = None

    # TODO: VERIFY results — what did the last VERIFY find?
    # last_verify: Optional[VerifyReport] = None
    # catastrophes: List[str] = field(default_factory=list)  # A-E classes
    # sha_count: int = 0  # |Ш| — non-liftable obstructions

    @property
    def y_layer(self) -> str:
        """Current Y-layer based on Griess phase."""
        return PHASE_TO_Y.get(self.phase, "")

    @property
    def is_verified(self) -> bool:
        """Has this concept passed VERIFY at least once?"""
        return self.ses_depth > 0 or self.phase in (
            GriessPhase.ONT,
            GriessPhase.PATTERN,
            GriessPhase.IMPLEMENT,
        )

    @property
    def has_kappa(self) -> bool:
        """Has a target Aut group been declared?"""
        return self.kappa is not None and len(self.kappa.invariants) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase.value,
            "y_layer": self.y_layer,
            "ses_depth": self.ses_depth,
            "is_verified": self.is_verified,
            "has_kappa": self.has_kappa,
            "kappa": self.kappa.to_dict() if self.kappa else None,
            "history": self.history,
        }


# ═══════════════════════════════════════════════════════════════
# VERIFY REPORT — the Aut check
#
# This is the MEASUREMENT step. It answers:
#   "Is Aut(what you built) = the κ_user you declared?"
#
# Three sub-checks:
#   1. YO correct: structural integrity (is_a chains close)
#   2. SES meaningful: typed depth > 0 (not all arbitrary strings)
#   3. Strong compression: has MSC + all relationships justified
#
# TODO: Add κ_user invariant checking:
#   4. κ preserved: each declared invariant still holds
#   5. Catastrophe class: which A-E class describes any failure
#   6. |Ш| count: how many non-liftable obstructions remain
# ═══════════════════════════════════════════════════════════════

@dataclass
class VerifyReport:
    """Results of the VERIFY step — the Aut check.

    Callers build this from actual YOUKNOW machinery:
      - yo_correct: from Cat_of_Cat.is_declared_bounded() + O-strata validation
      - ses_meaningful: from compute_ses_typed_depth().max_typed_depth > 0
      - strong_compression: from CompressionReport (has_msc + all_required_justified)
    """
    # Structural checks (existing)
    yo_correct: bool
    ses_meaningful: bool
    strong_compression: bool
    yo_reason: str = ""
    ses_reason: str = ""
    compression_reason: str = ""

    # TODO: κ_user invariant checks
    # kappa_preserved: bool = True
    # kappa_violations: List[str] = field(default_factory=list)
    # Each violation = one invariant that Aut(algebra) doesn't preserve
    # These map directly to catastrophe classes:
    #   A: "done" asserted but invariant not actually preserved
    #   B: inherited wrong assumption about what κ_user is
    #   C: same invariant label, different actual meaning
    #   D: invariant was preserved but the proof was lost
    #   E: invariant preserved but in increasingly generic way

    # TODO: |Ш| computation
    # sha: int = 0  # Non-liftable obstructions
    # Each Ш element = an invariant that LOOKS preserved locally
    # but fails globally. Customer says "it works" in testing
    # but fails in production. Locally valid, globally broken.

    @property
    def passes(self) -> bool:
        """Does this report pass all checks?"""
        return self.yo_correct and self.ses_meaningful and self.strong_compression

    def to_dict(self) -> Dict[str, Any]:
        return {
            "yo_correct": self.yo_correct,
            "yo_reason": self.yo_reason,
            "ses_meaningful": self.ses_meaningful,
            "ses_reason": self.ses_reason,
            "strong_compression": self.strong_compression,
            "compression_reason": self.compression_reason,
            "passes": self.passes,
        }


# ═══════════════════════════════════════════════════════════════
# THE COMPILER
#
# Current: a tracker (records which phase each concept is at)
# Target:  a compiler (takes κ_user, outputs guarded state machine)
#
# The compiler should:
#   1. Accept κ_user declaration (DERIVE input)
#   2. Derive constraints from κ_user (COMPUTE)
#   3. Construct minimal algebra (BUILD)
#   4. Check Aut(algebra) = κ_user (VERIFY)
#   5. If yes → ONT → reify → SES+1
#   6. If no → SOUP → return which invariant broke + catastrophe class
#
# When iterated via SES+1, the compiler compiles instruction sets
# for compilers — it becomes a meta-compiler. This is the Futamura
# tower applied to product construction.
# ═══════════════════════════════════════════════════════════════

class GriessConstructor:
    """State machine compiler for domain construction.

    Takes a declared target automorphism group (κ_user) and
    guides construction of an algebra whose Aut = κ_user.

    The state machine enforces: you cannot build without first
    declaring what you're building for. You cannot keep building
    when you should be verifying. Each phase has exactly one
    valid next phase.
    """

    def __init__(self):
        self.concepts: Dict[str, ConceptState] = {}

    # ─── DERIVE: Declare the target ──────────────────────────

    def register(self, name: str, phase: GriessPhase = GriessPhase.DERIVE) -> ConceptState:
        """Register a new concept at a given phase."""
        state = ConceptState(name=name, phase=phase)
        state.history.append(f"registered at {phase.value}")
        self.concepts[name] = state
        return state

    def declare_kappa(self, name: str, domain: str, invariants: Dict[str, str]) -> ConceptState:
        """DERIVE step: declare the target automorphism group.

        This is the most important step. Without it, VERIFY has
        nothing to check against. This is customer interviews.

        Args:
            name: concept name
            domain: what domain this is for (e.g., "fitness_app")
            invariants: what must be preserved
                e.g., {"user_gets_stronger": "measurable fitness progress"}
        """
        state = self.concepts.get(name)
        if state is None:
            state = self.register(name, GriessPhase.DERIVE)

        state.kappa = KappaUser(domain=domain, invariants=invariants)
        state.history.append(
            f"κ_user declared: {domain} with {len(invariants)} invariants"
        )
        return state

    # TODO: derive_constraints(name) → COMPUTE step
    #   Given κ_user, derive what the algebra MUST contain.
    #   This is where the LLM helps: "given these user invariants,
    #   what components/features/slots must the product have?"
    #   Output: a set of REQUIRED SLOTS that the algebra must fill.
    #   Maps to CB: bloom (slots appear from κ_user declaration).

    # TODO: build_algebra(name) → BUILD step
    #   Given constraints, construct the minimal algebra.
    #   This is where the LLM fills slots: content that satisfies
    #   the constraints derived from κ_user.
    #   Maps to CB: fill (LLM generates content for each slot).

    # ─── State Machine ───────────────────────────────────────

    def get(self, name: str) -> Optional[ConceptState]:
        """Get a concept's current state."""
        return self.concepts.get(name)

    def advance(self, name: str, to_phase: GriessPhase, reason: str = "") -> ConceptState:
        """Advance a concept to the next phase.

        The state machine enforces valid transitions.
        You CANNOT go BUILD → BUILD. The only exit from BUILD is VERIFY.

        Returns the updated state.
        Raises ValueError if the transition is not valid.
        """
        state = self.concepts.get(name)
        if state is None:
            raise ValueError(f"Concept '{name}' not registered")

        valid_next = TRANSITIONS.get(state.phase, [])
        if to_phase not in valid_next:
            raise ValueError(
                f"Invalid transition: {state.phase.value} → {to_phase.value}. "
                f"Valid: {[p.value for p in valid_next]}"
            )

        # Guard: cannot leave DERIVE without κ_user
        if state.phase == GriessPhase.DERIVE and not state.has_kappa:
            raise ValueError(
                f"Cannot leave DERIVE without declaring κ_user. "
                f"Call declare_kappa() first. "
                f"You must say what you're building for."
            )

        old_phase = state.phase
        state.phase = to_phase

        # Track SES depth: increment when cycling through IMPLEMENT → DERIVE
        if old_phase == GriessPhase.IMPLEMENT and to_phase == GriessPhase.DERIVE:
            state.ses_depth += 1

        transition_key = f"{old_phase.value}→{to_phase.value}"
        condition = TRANSITION_CONDITIONS.get(transition_key, "")
        entry = f"{old_phase.value} → {to_phase.value}"
        if reason:
            entry += f" ({reason})"
        if condition:
            entry += f" [condition: {condition}]"
        state.history.append(entry)

        return state

    def from_emr(self, name: str, emr_state: str) -> Optional[GriessPhase]:
        """Map an EMR state to the corresponding Griess phase."""
        return EMR_TO_PHASE.get(emr_state)

    def advance_from_emr(self, name: str, emr_state: str) -> Optional[ConceptState]:
        """Advance a concept based on its EMR state."""
        target_phase = self.from_emr(name, emr_state)
        if target_phase is None:
            return None

        state = self.concepts.get(name)
        if state is None:
            return self.register(name, target_phase)

        valid_next = TRANSITIONS.get(state.phase, [])
        if target_phase in valid_next:
            return self.advance(name, target_phase, reason=f"EMR={emr_state}")

        return state

    # ─── VERIFY: The Aut Check ────────────────────────────────

    def verify(self, name: str, report: VerifyReport) -> ConceptState:
        """Run the Griess VERIFY step for a concept.

        This is the MEASUREMENT. It checks:
          1. YO correct: structural integrity
          2. SES meaningful: typed depth > 0
          3. Strong compression: has MSC + justified relationships

        TODO: Add κ_user invariant check:
          4. Each declared invariant still holds in Aut(algebra)
          5. Map failures to catastrophe classes A-E
          6. Compute |Ш| from locally-valid-globally-broken invariants

        If all pass → ONT (Aut closes. Ship it.)
        If any fail → SOUP (tells you exactly what broke and why)
        """
        state = self.concepts.get(name)
        if state is None:
            raise ValueError(f"Concept '{name}' not registered")
        if state.phase != GriessPhase.VERIFY:
            raise ValueError(
                f"Concept '{name}' is at {state.phase.value}, not VERIFY"
            )

        failures = []

        # 1. YO: structural integrity
        if not report.yo_correct:
            failures.append(
                f"YO structure wrong: {report.yo_reason or 'is_a chain does not close'}"
            )

        # 2. SES: typed depth is meaningful
        if not report.ses_meaningful:
            failures.append(
                f"SES not meaningful: {report.ses_reason or 'ses_typed_depth=0'}"
            )

        # 3. Strong compression
        if not report.strong_compression:
            failures.append(
                f"Weak compression: {report.compression_reason or 'missing MSC'}"
            )

        # TODO: 4. κ_user invariant check
        # if state.has_kappa:
        #     for inv_name, inv_desc in state.kappa.invariants.items():
        #         if not check_invariant_preserved(name, inv_name):
        #             failures.append(f"κ violation: {inv_name} not preserved")

        if failures:
            reason = "; ".join(failures)
            return self.advance(name, GriessPhase.SOUP, reason=reason)
        else:
            return self.advance(
                name, GriessPhase.ONT,
                reason="Aut closes: all checks pass"
            )

    # ─── Queries ──────────────────────────────────────────────

    def get_by_phase(self, phase: GriessPhase) -> List[ConceptState]:
        """Get all concepts at a given phase."""
        return [s for s in self.concepts.values() if s.phase == phase]

    def get_by_y_layer(self, y_layer: str) -> List[ConceptState]:
        """Get all concepts at a given Y-layer."""
        return [s for s in self.concepts.values() if s.y_layer == y_layer]

    def get_verified(self) -> List[ConceptState]:
        """Get all concepts that have passed VERIFY at least once."""
        return [s for s in self.concepts.values() if s.is_verified]

    def get_stuck_in_build(self) -> List[ConceptState]:
        """Get concepts stuck in BUILD (should be moving to VERIFY).

        These are the spinning concepts — they have enough algebra
        but haven't measured yet. The state machine says: VERIFY next.
        """
        return [
            s for s in self.concepts.values()
            if s.phase == GriessPhase.BUILD
        ]

    def get_without_kappa(self) -> List[ConceptState]:
        """Get concepts that have no declared κ_user.

        These are building without a target. VERIFY will fail because
        there's nothing to check against. They need declare_kappa().
        """
        return [
            s for s in self.concepts.values()
            if not s.has_kappa
        ]

    def status(self) -> Dict[str, Any]:
        """Get current status of the compiler."""
        phase_counts = {}
        for phase in GriessPhase:
            concepts = self.get_by_phase(phase)
            if concepts:
                phase_counts[phase.value] = [c.name for c in concepts]

        return {
            "total_concepts": len(self.concepts),
            "phases": phase_counts,
            "verified_count": len(self.get_verified()),
            "stuck_in_build": [c.name for c in self.get_stuck_in_build()],
            "missing_kappa": [c.name for c in self.get_without_kappa()],
            "max_ses_depth": max(
                (s.ses_depth for s in self.concepts.values()), default=0
            ),
        }

    # TODO: compile(name) → full compiler pass
    #   Run the complete construction:
    #     1. Check κ_user is declared (DERIVE)
    #     2. Derive constraints from κ_user via LLM (COMPUTE)
    #     3. Create CB space + bloom slots (BUILD)
    #     4. Fill slots via LLM (BUILD)
    #     5. Lock + mine + check Aut (VERIFY)
    #     6. Return ONT or SOUP with diagnostics
    #
    #   This is the single-pass compiler. SES+1 would iterate it.

    # TODO: meta_compile(name) → Futamura iteration
    #   Run compile() on the OUTPUT of a previous compile().
    #   Level 0: compile(product) → specific product
    #   Level 1: compile(compiler_for_products) → product factory
    #   Level 2: compile(compiler_for_compilers) → meta-compiler
    #   Crown: compile(self) → fixed point


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_constructor: Optional[GriessConstructor] = None


def get_constructor() -> GriessConstructor:
    """Get the global Griess constructor instance."""
    global _constructor
    if _constructor is None:
        _constructor = GriessConstructor()
    return _constructor


def reset_constructor():
    """Reset the global constructor (for testing)."""
    global _constructor
    _constructor = None
