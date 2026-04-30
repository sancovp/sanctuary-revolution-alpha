"""Narrative arc models — Episode through Grand Odyssey.

Arc invariant: every arc at every level has a 3-act structure.
Sub-elements (scenes, episodes, journeys, epics, odysseys) are grouped
into act_1/act_2/act_3. Same shape, every level. Fractal.

The 3-act grouping follows HGS beat positions from GAS.
Beat/GoalSequence models are stubs — full versions exist in GAS Prolog
(foundation.pl) and will be ported when GAS→SOMA integration is done.

Scene claim rule: iteration part objects can only be composed into ONE scene.
Each scene must check has_scene on its source iterations before claiming.

Temporality: forward-only within each arc. No going back in time.

Each model maps 1:1 to a CartON concept type prefix:
  Episode_ → EpisodeArc
  Journey_ → JourneyArc
  Epic_    → EpicArc
  Odyssey_ → OdysseyArc
  Super_Odyssey_ → SuperOdysseyArc
  Grand_Odyssey_ → GrandOdysseyArc
  TWI_     → ThematicWisdomIntent
"""

from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from .scene_machine import SceneMachine, SceneModel


class NarrativeOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    INCOMPLETE = "incomplete"


class AesopType(str, Enum):
    """What kind of story this is — determines how the TWI reads."""
    WARNING = "warning"           # "if you do X, bad thing Y happens"
    CELEBRATION = "celebration"   # "doing X led to breakthrough Y"
    IRONY = "irony"               # "trying to avoid X caused X"
    GROWTH = "growth"             # "through struggle with X, gained Y"
    DISCOVERY = "discovery"       # "X was actually Y all along"


class TWIScope(str, Enum):
    """Where the TWI applies."""
    PROJECT = "project"   # evolves one starsystem's GIINT_Project
    GLOBAL = "global"     # evolves user.md, SOUL.md, global Prolog rules


# =============================================================================
# STUB — Beat positions from GAS HGS structure
# Full Beat/GoalSequence models exist in GAS Prolog (foundation.pl).
# These will be ported to Python when GAS→SOMA integration is done.
# For now, beat_position is a string field on scenes.
# =============================================================================

# Save the Cat / HGS beat positions — known positions in the 3-act structure.
# Scenes get tagged with one of these to determine which act they belong to.
# Act 1: opening_image through break_into_two
# Act 2: b_story through break_into_three
# Act 3: finale through final_image
BEAT_POSITIONS_ACT_1 = [
    "opening_image", "theme_stated", "setup", "catalyst",
    "debate", "break_into_two",
]
BEAT_POSITIONS_ACT_2 = [
    "b_story", "fun_and_games", "midpoint",
    "bad_guys_close_in", "all_is_lost", "dark_night_of_the_soul",
    "break_into_three",
]
BEAT_POSITIONS_ACT_3 = [
    "finale", "final_image",
]


# =============================================================================
# Dialog — raw conversation moments preserved with exact quotes
# =============================================================================

class Dialog(BaseModel):
    """A key conversation moment extracted from raw iterations."""
    speaker: Literal["human", "agent", "system"]
    content: str  # THE EXACT QUOTE
    context: Optional[str] = None  # WHY this moment matters
    source_iteration: str  # CartON concept name of source iteration
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Arc — the base invariant shared by every narrative level
# =============================================================================

class Arc(BaseModel):
    """Base arc — the invariant that makes something an arc.

    Every arc at every level has:
    - 3-act structure (sub-elements grouped into acts)
    - Entry/exit states (the transformation)
    - Theme (the argument this arc proves)
    - TWI refs (which intents this arc tests)
    - Outcome

    Sub-elements are strings (CartON concept refs). For EpisodeArc,
    sub-elements are scene refs. For JourneyArc, episode refs. Etc.
    The union of act_1 + act_2 + act_3 IS the complete list.
    """
    arc_id: str
    title: str
    summary: str = ""

    # The 3-act invariant — sub-element refs grouped by act position
    act_1: List[str] = Field(default_factory=list, description="Setup — sub-element refs")
    act_2: List[str] = Field(default_factory=list, description="Confrontation — sub-element refs")
    act_3: List[str] = Field(default_factory=list, description="Resolution — sub-element refs")

    # Transformation
    entry_state: str = Field(default="", description="State at the start of this arc")
    exit_state: str = Field(default="", description="State at the end of this arc")

    # Theme / argument
    theme: str = Field(default="", description="The argument this arc proves — emerges from TWI comparison")
    twis: List[str] = Field(default_factory=list, description="TWI refs tested by this arc")

    # Central conflict — the thing that made this arc LONGER than it should've been
    central_conflict: str = Field(default="", description="The internal obstacle — always a TWI violation pattern")

    outcome: NarrativeOutcome = NarrativeOutcome.INCOMPLETE
    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Narrative hierarchy: Episode → Journey → Epic → Odyssey → Super → Grand
# Each inherits Arc invariant + adds level-specific fields
# =============================================================================

class EpisodeArc(Arc):
    """Aggregates scenes across conversations by topic (TWI or task).

    NOT 1:1 with conversations. An episode pulls scenes from whatever
    conversations touched this topic. Scenes are extracted from iterations
    by comparing against TWIs — alignment = advancement, violation = conflict.

    Scene claim rule: iteration parts can only compose into ONE scene.
    claimed_iterations tracks what's been used.
    """
    starsystem: str = ""
    starlog_session_id: Optional[str] = None
    giint_path: Optional[str] = None

    # The scenes — each has a SceneMachine (8-node dramatic flow)
    # Scenes are grouped into acts via act_1/act_2/act_3 (scene concept refs)
    scenes: List[SceneModel] = Field(default_factory=list)

    # Scene claim tracking — iteration parts can only be in ONE scene
    claimed_iterations: List[str] = Field(
        default_factory=list,
        description="Iteration concept refs already claimed by scenes in this episode"
    )

    # Source material
    source_phases: List[str] = Field(default_factory=list, description="L4 phase CartON refs")
    # NOTE: Dialogs live at the SCENE level, not episode level.
    # Dialog concepts are PART_OF their scene in CartON graph.
    # The SDNAC agents create Dialog concepts with part_of=Scene_*.
    concepts: List[str] = Field(default_factory=list)


class JourneyArc(Arc):
    """Aggregates Episodes about the same GIINT_Component into a 3-act Hero's Journey.

    act_1/act_2/act_3 contain episode refs grouped by act position.
    Boon = the ONE transferable framework extracted. Boon IS a framework
    that becomes an infoproduct → starsystem plugin.

    A single episode CAN be a journey if it contains a complete 3-act structure.
    """
    component_name: str = ""  # GIINT_Component name
    starsystem: str = ""

    boon: str = Field(default="", description="The framework extracted — becomes infoproduct")
    key_learnings: List[str] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)


class EpicArc(Arc):
    """Aggregates Journeys about the same GIINT_Feature into a feature-level arc.

    act_1/act_2/act_3 contain journey refs. One journey CANNOT be an epic alone
    (except as a base version building toward a future epic).
    """
    feature_name: str = ""  # GIINT_Feature name
    starsystem: str = ""

    boon: str = Field(default="", description="Feature-level boon")
    key_learnings: List[str] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)


class OdysseyArc(Arc):
    """Aggregates Epics into the story of a GIINT_Project.

    act_1/act_2/act_3 contain epic refs. One epic CANNOT be an odyssey alone
    (except as base version). The Odyssey IS the narrative system's top-level
    output per starsystem.
    """
    project_name: str = ""  # GIINT_Project name
    starsystem: str = ""

    concepts: List[str] = Field(default_factory=list)


class SuperOdysseyArc(Arc):
    """TRUE AGENT lifetime — aggregates Odysseys across ALL starsystems.

    act_1/act_2/act_3 contain odyssey refs.
    Global TWIs evolve user.md, SOUL.md, global Prolog rules.
    The Super Odyssey IS the TRUE AGENT cognizing itself.
    """
    global_twis: List[str] = Field(default_factory=list)


class GrandOdysseyArc(Arc):
    """Dual protagonist compound narrative — system + user merged.

    The GrandOdyssey IS the namthar. Merges system SuperOdyssey with user's
    life narrative via Saturday friendship ritual. Finds retroactive continuity
    across both protagonist tracks.

    act_1/act_2/act_3 here span BOTH protagonist tracks.
    """
    system_super_odyssey: Optional[str] = None  # SuperOdysseyArc ref
    user_super_odyssey: Optional[str] = None  # User's life narrative ref

    combined_twis: List[str] = Field(default_factory=list)


# =============================================================================
# TWI — Thematic Wisdom Intent (the Grand Argument extracted by AC)
# =============================================================================

class ThematicWisdomIntent(BaseModel):
    """The Grand Argument extracted from accumulated narrative by AC.

    Not "the moral." The AUTOLOGICAL CONSTRAINT the story reveals:
    applies to everything INCLUDING itself.

    AC flow: Heat (many epics) → Stack (different domains sharing structure)
    → Triangulation (universal structure) → Click → Equipment (TWI as rule)

    Dramatica: thesis + because + inner obstacle + external obstacles
    + storyform + type = Grand Argument = aesop about our intents.
    """
    twi_id: str
    theme: str = Field(description="Thesis — 'in order to X you must Y'")
    because: str = Field(description="Why this theme holds for US")
    inner_obstacle: str = Field(description="Psychological pattern that created the theme")
    external_obstacles: List[str] = Field(
        default_factory=list,
        description="Practical manifestations of the inner obstacle"
    )
    grand_argument: str = Field(
        default="",
        description="Full Dramatica storyform summary — how this plays out as a complete structure"
    )
    aesop_type: AesopType = AesopType.GROWTH
    scope: TWIScope = TWIScope.PROJECT

    # What it produces
    rule_type: Optional[Literal["claude_code_rule", "prolog_rule"]] = None
    rule_content: Optional[str] = None  # the actual rule body

    # Provenance
    source_epics: List[str] = Field(default_factory=list, description="Which epics were triangulated")
    source_odyssey: Optional[str] = None  # which odyssey this came from

    created_at: datetime = Field(default_factory=datetime.now)
