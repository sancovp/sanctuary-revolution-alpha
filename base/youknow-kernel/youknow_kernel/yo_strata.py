"""
YO-Strata State Machine

The Griess Constructor-backed Y-strata × O-strata system.
Replaces the neural Y-Mesh activation model with a deterministic
state machine based on the Griess construction phases.

O-strata (HAS_A) is the CONSTRUCTOR — the program.
Y-strata (IS_A) is the CONSTRUCTED — the output.
O builds Y homoiconically via self-application.

Bootstrap: O → UARL chains → domain ontology emerges →
           self-application → Y emerges → Y1-Y4 → Y4 fixed point →
           Y5-Y6 meta-compilation

Same outward API as y_mesh.py so the compiler can swap imports.
y_mesh.py is preserved for future neural/training use.
"""

from typing import Dict, List, Optional, Any
from enum import Enum

from .griess_constructor import (
    GriessConstructor,
    GriessPhase,
    ConceptState,
    VerifyReport,
    get_constructor,
    PHASE_TO_Y,
    EMR_TO_PHASE,
)


# ─── Re-export YLayer for compatibility ───────────────────────────

class YLayer(str, Enum):
    """The six Y-strata layers (compatible with y_mesh.YLayer)."""
    Y1_UPPER = "y1"
    Y2_DOMAIN = "y2"
    Y3_APPLICATION = "y3"
    Y4_INSTANCE = "y4"
    Y5_PATTERN = "y5"
    Y6_IMPLEMENTATION = "y6"


# Griess phase → YLayer mapping
_PHASE_TO_YLAYER = {
    GriessPhase.DERIVE: YLayer.Y1_UPPER,
    GriessPhase.COMPUTE: YLayer.Y2_DOMAIN,
    GriessPhase.BUILD: YLayer.Y3_APPLICATION,
    GriessPhase.VERIFY: YLayer.Y4_INSTANCE,
    GriessPhase.PATTERN: YLayer.Y5_PATTERN,
    GriessPhase.IMPLEMENT: YLayer.Y6_IMPLEMENTATION,
}

# EMR → YLayer (via Griess phase)
_EMR_TO_YLAYER = {
    "embodies": YLayer.Y1_UPPER,       # DERIVE
    "manifests": YLayer.Y2_DOMAIN,     # COMPUTE
    "reifies": YLayer.Y3_APPLICATION,  # BUILD
    "programs": YLayer.Y4_INSTANCE,    # VERIFY
}


# ─── Telemetry (compiler-facing API) ──────────────────────────────

def build_compile_telemetry(
    concept_name: str,
    emr_state: str,
    admit_to_ont: bool,
) -> Dict[str, Any]:
    """Build controller telemetry for compile packet diagnostics.

    Drop-in replacement for y_mesh.build_compile_telemetry.
    Backed by actual Griess state instead of fake activation floats.
    """
    gc = get_constructor()
    concept = gc.get(concept_name)

    # Auto-register if not tracked yet
    if concept is None:
        target_phase = EMR_TO_PHASE.get(emr_state, GriessPhase.DERIVE)
        concept = gc.register(concept_name, target_phase)
    else:
        # Try to advance based on EMR
        gc.advance_from_emr(concept_name, emr_state)
        concept = gc.get(concept_name)

    phase = concept.phase
    y_layer = _PHASE_TO_YLAYER.get(phase, YLayer.Y4_INSTANCE)

    # Griess phase → activation equivalent (for backward compat)
    activation_map = {
        GriessPhase.DERIVE: 0.25,
        GriessPhase.COMPUTE: 0.55,
        GriessPhase.BUILD: 0.75,
        GriessPhase.VERIFY: 0.95,
        GriessPhase.ONT: 1.0,
        GriessPhase.PATTERN: 0.85,
        GriessPhase.IMPLEMENT: 0.90,
        GriessPhase.SOUP: 0.10,
    }
    activation = activation_map.get(phase, 0.25)
    codegen_threshold = 0.8  # kept for compat

    threshold_event = (
        phase in (GriessPhase.VERIFY, GriessPhase.ONT, GriessPhase.IMPLEMENT)
        and activation >= codegen_threshold
    )

    if admit_to_ont:
        transition = "SOUP_TO_ONT"
        gate_outcome = "admit_to_ont"
    else:
        transition = "STAY_SOUP"
        gate_outcome = "stay_in_soup"

    return {
        "concept_name": concept_name,
        "emr_state": emr_state,
        "target_layer": y_layer.value,
        "activation": activation,
        "codegen_threshold": codegen_threshold,
        "threshold_event": threshold_event,
        "transition": transition,
        "gate_outcome": gate_outcome,
        # New fields from Griess state machine
        "griess_phase": phase.value,
        "ses_depth": concept.ses_depth,
        "is_verified": concept.is_verified,
    }


# ─── YOStrata SM (the main class) ────────────────────────────────

class YOStrata:
    """YO-Strata state machine.

    Organizes concepts by Griess construction phase.
    O-strata (HAS) builds Y-strata (IS) via self-application.

    Compatible with YMesh API where needed, but backed by
    the Griess Constructor instead of neural activation.
    """

    def __init__(self):
        self.gc = GriessConstructor()

    def add_node(
        self,
        layer: YLayer,
        name: str,
        content: Dict = None,
        is_a: List[str] = None,
        has_part: List[str] = None,
    ):
        """Add a concept, inferring Griess phase from Y-layer.

        Compatible with YMesh.add_node() signature.
        """
        # Map YLayer back to Griess phase
        ylayer_to_phase = {v: k for k, v in _PHASE_TO_YLAYER.items()}
        phase = ylayer_to_phase.get(layer, GriessPhase.DERIVE)

        existing = self.gc.get(name)
        if existing is None:
            self.gc.register(name, phase)
        return self.gc.get(name)

    def register(self, name: str, emr_state: str = "embodies") -> ConceptState:
        """Register a concept from its EMR state."""
        phase = EMR_TO_PHASE.get(emr_state, GriessPhase.DERIVE)
        return self.gc.register(name, phase)

    def advance(self, name: str, emr_state: str) -> Optional[ConceptState]:
        """Advance a concept based on EMR state."""
        return self.gc.advance_from_emr(name, emr_state)

    def verify(self, name: str, report: VerifyReport) -> ConceptState:
        """Run Griess VERIFY on a concept."""
        return self.gc.verify(name, report)

    def get_phase(self, name: str) -> Optional[GriessPhase]:
        """Get a concept's current Griess phase."""
        state = self.gc.get(name)
        return state.phase if state else None

    def get_y_layer(self, name: str) -> Optional[YLayer]:
        """Get a concept's current Y-layer."""
        state = self.gc.get(name)
        if state is None:
            return None
        return _PHASE_TO_YLAYER.get(state.phase)

    def get_ses_depth(self, name: str) -> int:
        """Get a concept's SES depth."""
        state = self.gc.get(name)
        return state.ses_depth if state else 0

    def codegen_ready(self, name: str) -> bool:
        """Is this concept ready for codegen? (VERIFY passed)"""
        state = self.gc.get(name)
        return state.is_verified if state else False

    def get_ready_for_codegen(self) -> List[str]:
        """Get all concepts ready for codegen."""
        return [s.name for s in self.gc.get_verified()]

    def get_status(self) -> Dict[str, Any]:
        """Get current strata status."""
        status = self.gc.status()
        # Add Y-layer view
        y_view = {}
        for layer in YLayer:
            concepts = self.gc.get_by_y_layer(layer.value.upper())
            if concepts:
                y_view[layer.value] = [c.name for c in concepts]
        status["y_layers"] = y_view
        return status


# ─── Module-level singleton ───────────────────────────────────────

_yo_strata: Optional[YOStrata] = None


def get_yo_strata() -> YOStrata:
    """Get the global YOStrata instance."""
    global _yo_strata
    if _yo_strata is None:
        _yo_strata = YOStrata()
    return _yo_strata


def reset_yo_strata():
    """Reset the global instance (for testing)."""
    global _yo_strata
    _yo_strata = None
