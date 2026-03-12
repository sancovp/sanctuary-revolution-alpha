"""Sanctuary Revolution - Victory-Everything Chains.

The game layer that encodes the entire phase space transformation journey.
Re-exports from youknow-kernel, sanctuary-system, and provides the harness.
"""

from .models import (
    # From youknow-kernel
    YOUKNOW, Entity, PIOEntity, ValidationLevel, InteractionMode,
    SelfSimulationLevel, SuperclassChain, create_root_entities,
    CategoryStructure, Morphism, CertaintyState, ValidationResult,
    validate_pattern_of_isa, llm_suggest,
    Chain, Link, LinkType, DualLoop, core_sentence_chain,
    chain_from_validation_result, dual_loop_from_entity,
    # From sanctuary-system
    SanctuaryEntity, MiniGame, GamePhase, AllegoryMapping,
    SANCREVTWILITELANGMAP, SanctuaryJourney, MVS, VEC,
    PlayerState, MINIGAME_TRANSITIONS,
    # Facade
    SanctuaryOntology,
)

from .core import SanctuaryRevolution

# Omnisanc - state machine tracking
from .omnisanc_state import (
    OmnisancPhase,
    LandingStep,
    CourseState,
    load_course_state,
    get_phase,
    is_home,
    is_in_session,
    is_landing,
)

# Harness - sancrev-specific components only
# Runtime control (harness, hooks, events etc) now in cave-harness
from .harness import (
    PersonaControl,
    PERSONA_FLAG,
)

__all__ = [
    "SanctuaryRevolution",
    # youknow-kernel
    "YOUKNOW", "Entity", "PIOEntity", "ValidationLevel", "InteractionMode",
    "SelfSimulationLevel", "SuperclassChain", "create_root_entities",
    "CategoryStructure", "Morphism", "CertaintyState", "ValidationResult",
    "validate_pattern_of_isa", "llm_suggest",
    "Chain", "Link", "LinkType", "DualLoop", "core_sentence_chain",
    "chain_from_validation_result", "dual_loop_from_entity",
    # sanctuary-system
    "SanctuaryEntity", "MiniGame", "GamePhase", "AllegoryMapping",
    "SANCREVTWILITELANGMAP", "SanctuaryJourney", "MVS", "VEC",
    "PlayerState", "MINIGAME_TRANSITIONS",
    # facade
    "SanctuaryOntology",
    # omnisanc state machine
    "OmnisancPhase",
    "LandingStep",
    "CourseState",
    "load_course_state",
    "get_phase",
    "is_home",
    "is_in_session",
    "is_landing",
    # harness (sancrev-specific)
    "PersonaControl",
    "PERSONA_FLAG",
]

__version__ = "0.5.0"
