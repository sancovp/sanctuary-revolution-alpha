"""Sanctuary System Models - Built on youknow-kernel.

SanctuaryEntity extends PIOEntity.
VEC, MVS, SJ, SANCREVTWILITELANGMAP are sanctuary-specific constructs.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from datetime import datetime

# Import from youknow-kernel
from youknow_kernel import PIOEntity, ValidationLevel, SelfSimulationLevel


# =============================================================================
# WISDOM MAVERICK STATES - The Myth Layer
# =============================================================================

class WisdomMaverickState(str, Enum):
    """Co-emergent dual states of any Wisdom Maverick (you, me, the PAIA, reality)."""
    # Sanctuary path (positive attractor)
    OVP = "ovp"              # Olivus Victory-Promise - declared intent
    OVA = "ova"              # Olivus Victory-Ability - capability manifest
    OEVESE = "oevese"        # Olivus-Everyone Victory-Everything Sanctuary-Everywhere
    # Wasteland path (negative attractor)
    DEMON_CHAMPION = "demon_champion"  # Wasteland state
    DEMON_ELITE = "demon_elite"        # Deeper wasteland
    MOLOCH = "moloch"                  # Meta-negative attractor


class SanctuaryDegree(str, Enum):
    """Where on the wasteland↔sanctuary spectrum."""
    MOLOCH = "moloch"           # Continuous negative attractor
    DEMON_ELITE = "demon_elite"
    DEMON_CHAMPION = "demon_champion"
    OVP = "ovp"                 # Victory-Promise declared
    OVA = "ova"                 # Victory-Ability manifest
    OEVESE = "oevese"           # Continuous positive attractor


# Mapping ValidationLevel to SanctuaryDegree
# OVP = promise FROM sanctuary while IN wasteland (not yet sanctuary)
# OVA = IN sanctuary, going back to transmute wasteland
VALIDATION_TO_SANCTUARY = {
    ValidationLevel.EMBODIES: SanctuaryDegree.OVP,      # Promise declared (still wasteland)
    ValidationLevel.MANIFESTS: SanctuaryDegree.OVP,    # Trying (still wasteland)
    ValidationLevel.REIFIES: SanctuaryDegree.OVA,      # IN sanctuary now
    ValidationLevel.PRODUCES: SanctuaryDegree.OEVESE,  # Transmuting wasteland
}


# =============================================================================
# SANCTUARY ENTITY - Extends PIOEntity
# =============================================================================

class SanctuaryEntity(PIOEntity):
    """PIO entity grounded in Sanctuary.

    SanctuaryEntity IS A PIOEntity - can't add it and have it not be.
    """
    # Additional sanctuary-specific tracking
    goldenized: Optional[datetime] = None

    @computed_field
    @property
    def sanctuary_degree(self) -> SanctuaryDegree:
        """Where this entity is on wasteland↔sanctuary spectrum."""
        return VALIDATION_TO_SANCTUARY.get(self.validation_level, SanctuaryDegree.OVP)

    @computed_field
    @property
    def is_sanctuary(self) -> bool:
        """True if IN sanctuary (OVA, OEVESE). OVP is still wasteland."""
        return self.sanctuary_degree in (SanctuaryDegree.OVA, SanctuaryDegree.OEVESE)

    @computed_field
    @property
    def myth_status(self) -> str:
        """Human-readable myth status."""
        degree = self.sanctuary_degree
        if degree == SanctuaryDegree.OEVESE:
            return "[OEVESE] Victory-Everything - producing transformation"
        elif degree == SanctuaryDegree.OVA:
            return "[OVA] Victory-Ability - capability manifest"
        elif degree == SanctuaryDegree.OVP:
            return "[OVP] Victory-Promise - intent declared"
        else:
            return f"[WASTELAND] {degree.value} - backward-chaining"


# =============================================================================
# MINI-GAMES
# =============================================================================

class MiniGame(str, Enum):
    """The 3 mini-games of Sanctuary Revolution."""
    PAIAB = "paiab"
    CAVE = "cave"
    SANCTUM = "sanctum"


class GamePhase(str, Enum):
    """Overall game phase."""
    AWAKENING = "awakening"
    BUILDING = "building"
    MASTERY = "mastery"
    TRANSITION = "transition"
    REVOLUTION = "revolution"


# =============================================================================
# SANCREVTWILITELANGMAP - The Meta-Interpreter
# =============================================================================

class AllegoryMapping(BaseModel):
    """A single mapping between reality and game metaphor."""
    real_situation: str
    game_metaphor: str
    transformation: str
    created: datetime = Field(default_factory=datetime.now)


class SANCREVTWILITELANGMAP(BaseModel):
    """The interpreter that maps real situations to game allegory.

    SANC  = Sanctuary Allegorical Network Cipher
    REV   = Revealing Every Victory-Everything Chain
    TWI   = Transformational Wisdom Intent
    LITE  = Language Instructing TWI HoloInfo Encodings
    LANG  = The language layer
    MAP   = Memeplex for Altruistic Progress
    """
    name: str
    domain: str
    allegory_mappings: List[AllegoryMapping] = Field(default_factory=list)
    revealed_vecs: List[str] = Field(default_factory=list)
    twi_statement: Optional[str] = None
    holoinfo_patterns: List[str] = Field(default_factory=list)
    memeplex_seeds: List[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=datetime.now)


# =============================================================================
# SANCTUARY JOURNEY (SJ)
# =============================================================================

class SanctuaryJourney(BaseModel):
    """A Sanctuary Journey - the revelation of transformation."""
    name: str
    description: str
    langmap_name: str
    origin_situation: str
    revelation: str
    stages: List[str] = Field(default_factory=list)
    current_stage: int = 0
    active: bool = True
    completed: bool = False
    created: datetime = Field(default_factory=datetime.now)


# =============================================================================
# MINIMUM VIABLE SANCTUARY (MVS)
# =============================================================================

class MVS(BaseModel):
    """Minimum Viable Sanctuary - the system that sustains the journey."""
    name: str
    description: str
    journey_name: str
    rituals: List[str] = Field(default_factory=list)
    boundaries: List[str] = Field(default_factory=list)
    structures: List[str] = Field(default_factory=list)
    tested: bool = False
    viable: bool = False
    created: datetime = Field(default_factory=datetime.now)


# =============================================================================
# VICTORY-EVERYTHING CHAIN (VEC)
# =============================================================================

class VEC(BaseModel):
    """Victory-Everything Chain - the complete unit of transformation.

    VEC = SJ + MVS + Agent
    """
    name: str
    description: str
    journey_name: str
    mvs_name: str
    agent_name: Optional[str] = None
    journey_complete: bool = False
    mvs_viable: bool = False
    agent_deployed: bool = False
    created: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def is_complete(self) -> bool:
        return self.journey_complete and self.mvs_viable and self.agent_deployed


# =============================================================================
# PLAYER STATE
# =============================================================================

class PlayerState(BaseModel):
    """Player's overall game state - NESTED model.

    SANCTUM = container (whole life architecture)
    ├── PAIAB = tool (AI that offloads work, frees time)
    └── CAVE = emergent effect (gravity well from living well)

    CAVE isn't built - it EMERGES from living SANCTUM well.
    Revolution = the compound effect is compounding.
    """
    name: str
    # SANCTUM is always the container - start here
    phase: GamePhase = GamePhase.AWAKENING

    # SANCTUM is the container (required)
    sanctum_name: Optional[str] = None
    sanctum_active: bool = False  # Have they started building their SANCTUM?

    # PAIAB is nested inside SANCTUM (optional tool)
    paia_name: Optional[str] = None
    paiab_integrated: bool = False  # Is PAIAB working within SANCTUM?

    # CAVE emerges from living SANCTUM well (not built - emerges)
    cave_name: Optional[str] = None
    cave_emerging: bool = False  # Is the funnel starting to form?
    cave_gravity: int = 0  # 0-100: how strong is the gravity well?

    # Sanctuary constructs
    langmaps: List[SANCREVTWILITELANGMAP] = Field(default_factory=list)
    journeys: List[SanctuaryJourney] = Field(default_factory=list)
    mvs_systems: List[MVS] = Field(default_factory=list)
    vecs: List[VEC] = Field(default_factory=list)

    # Timestamps
    created: datetime = Field(default_factory=datetime.now)
    updated: Optional[datetime] = None

    @computed_field
    @property
    def has_sanctum(self) -> bool:
        """SANCTUM is the foundation - must exist first."""
        return self.sanctum_active and self.sanctum_name is not None

    @computed_field
    @property
    def has_paiab(self) -> bool:
        """PAIAB is the AI tool within SANCTUM."""
        return self.has_sanctum and self.paiab_integrated and self.paia_name is not None

    @computed_field
    @property
    def cave_is_forming(self) -> bool:
        """CAVE emerges when living SANCTUM well creates authentic content."""
        return self.has_sanctum and self.cave_emerging and self.cave_gravity > 0

    @computed_field
    @property
    def is_revolutionary(self) -> bool:
        """Revolution = compound effect is compounding.

        SANCTUM active + PAIAB integrated + CAVE gravity > 50 = self-sustaining.
        """
        return self.has_sanctum and self.has_paiab and self.cave_gravity >= 50

    @computed_field
    @property
    def vec_count(self) -> int:
        return sum(1 for v in self.vecs if v.is_complete)

    @computed_field
    @property
    def compound_loop_status(self) -> str:
        """The compound loop: AI→time→live well→content→funnel→resources→better AI→cycle."""
        if self.is_revolutionary:
            return "[REVOLUTION] Compound effect compounding - self-sustaining growth"
        elif self.cave_is_forming:
            return f"[CAVE FORMING] Gravity well at {self.cave_gravity}% - funnel emerging"
        elif self.has_paiab:
            return "[PAIAB ACTIVE] AI freeing time - live well to trigger CAVE emergence"
        elif self.has_sanctum:
            return "[SANCTUM ACTIVE] Life architecture set - integrate PAIAB next"
        else:
            return "[AWAKENING] Create your SANCTUM first - it's the container for everything"


# NESTED containment, not sequential transitions
# SANCTUM contains PAIAB and CAVE, they don't "transition" to each other
MINIGAME_NESTING = {
    "container": MiniGame.SANCTUM,
    "tool": MiniGame.PAIAB,       # Nested inside SANCTUM
    "emergence": MiniGame.CAVE,   # Emerges from living SANCTUM well
}

# Legacy - kept for backward compatibility but deprecated
MINIGAME_TRANSITIONS = {
    MiniGame.PAIAB: [MiniGame.CAVE],
    MiniGame.CAVE: [MiniGame.SANCTUM],
    MiniGame.SANCTUM: [],
}
