"""Sanctuary Revolution Models - Thin facade.

Re-exports from youknow-kernel and sanctuary-system.
"""

# Re-export from youknow-kernel
from youknow_kernel import (
    YOUKNOW,
    Entity,
    PIOEntity,
    ValidationLevel,
    InteractionMode,
    SelfSimulationLevel,
    SuperclassChain,
    create_root_entities,
    # SES
    CategoryStructure,
    Morphism,
    CertaintyState,
    ValidationResult,
    validate_pattern_of_isa,
    llm_suggest,
    # UCO
    Chain,
    Link,
    LinkType,
    DualLoop,
    core_sentence_chain,
    chain_from_validation_result,
    dual_loop_from_entity,
)

# Re-export from sanctuary-system
from sanctuary_system import (
    SanctuaryEntity,
    MiniGame,
    GamePhase,
    AllegoryMapping,
    SANCREVTWILITELANGMAP,
    SanctuaryJourney,
    MVS,
    VEC,
    PlayerState,
    MINIGAME_TRANSITIONS,
    MINIGAME_NESTING,
)


# =============================================================================
# SANCTUARY ONTOLOGY - The facade that ties it together
# =============================================================================

from pydantic import BaseModel, Field, computed_field, ConfigDict
from typing import List


class SanctuaryOntology(BaseModel):
    """The container for the entire typed ontology.

    SanctuaryOntology.youknow = the validator
    This is reality's pattern-recognition process made visible.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "SanctuaryOntology"
    youknow: YOUKNOW = Field(default_factory=YOUKNOW)

    @computed_field
    @property
    def sanctuary_entities(self) -> List[SanctuaryEntity]:
        """All fully reified entities."""
        return [
            e for e in self.youknow.entities.values()
            if e.validation_level == ValidationLevel.INSTANTIATES
        ]

    @computed_field
    @property
    def is_self_aware(self) -> bool:
        """Does YOUKNOW contain YOUKNOW?"""
        return self.youknow.contains_self

    def bootstrap_self_reference(self) -> None:
        """Add YOUKNOW to YOUKNOW."""
        self.youknow.bootstrap_self_reference()
