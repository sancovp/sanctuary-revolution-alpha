"""
Narrative Arc System — Clean models for Episode/Journey/Epic narratives.

Three-level hierarchy:
- EpisodeArc: Single work unit narrative (uses SceneMachine 8-node flow)
- JourneyArc: Component milestone narrative (aggregates episodes)
- EpicArc: Module milestone narrative (aggregates journeys)

Origin: Ported from /home/GOD/core/computer_use_demo/codebase_analyzer_system/narrative_system.py
Changes: RegistryService → CartON, BaseHeavenAgentReplicant → SDNA, 6-section template → SceneMachine

Works alongside:
- JourneyCore (core.py) = the JOURNEY arc (status_quo -> accomplishment + boon)
- SceneMachine (scene_machine.py) = the SCENE engine (8-node dramatic flow per scene)
- Odyssey (odyssey.py) = the PBML cycle (Plan→Build→Measure→Learn)

Data flow:
- L1 iteration summaries → Dialog extraction (raw conversation moments)
- L4 phase aggregations → Episode construction (phases become dramatic episodes)
- Episodes → Journeys → Epics (narrative rolls up)
"""

from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from scene_machine import SceneMachine


# === ENUMS ===

class NarrativeLevel(str, Enum):
    """Levels of narrative in the system."""
    EPISODE = "episode"
    JOURNEY = "journey"
    EPIC = "epic"


class NarrativeOutcome(str, Enum):
    """Possible outcomes for a narrative."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    INCOMPLETE = "incomplete"


# === DIALOG ===

class Dialog(BaseModel):
    """Dialog extracted from raw conversation histories (L1 iterations).

    These are the real human-AI exchange moments that make the narrative
    come alive. Extracted from raw iterations, not summaries.
    """
    speaker: Literal["human", "agent", "system"] = Field(
        ..., description="Who said this."
    )
    content: str = Field(
        ..., description="The dialog text."
    )
    context: Optional[str] = Field(
        default=None,
        description="Surrounding context explaining why this moment matters."
    )
    source_iteration: str = Field(
        ..., description="CartON concept name of the source iteration."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this was said."
    )


# === EPISODE ARC ===

class EpisodeArc(BaseModel):
    """Narrative about a single work unit — one dramatic scene.

    Each episode IS a SceneMachine execution: the 8-node dramatic flow
    applied to a real work session. Episodes are constructed from L4
    phase aggregations (the summarizer's phase-level output).

    Connection to summarizer pipeline:
    - L4 Phase Aggregator produces phase summaries
    - Each phase becomes an episode's raw material
    - SceneMachine structures the phase into dramatic beats
    - Dialogs are pulled from L1 raw iterations within the phase
    """
    episode_id: str = Field(
        ..., description="Unique identifier. Format: Episode_{conversation_id}_{N}"
    )
    title: str = Field(
        ..., description="Episode title — evocative, captures the dramatic essence."
    )
    summary: str = Field(
        ..., description="High-level summary of what happened."
    )

    # The dramatic structure
    scene: SceneMachine = Field(
        ..., description="The 8-node dramatic flow for this episode."
    )

    # Source material
    source_phases: List[str] = Field(
        default_factory=list,
        description="CartON concept names of L4 phases that fed this episode."
    )
    dialogs: List[Dialog] = Field(
        default_factory=list,
        description="Key dialog moments extracted from L1 raw iterations."
    )
    concepts: List[str] = Field(
        default_factory=list,
        description="CartON concept names relevant to this episode."
    )

    # Outcome
    outcome: NarrativeOutcome = Field(
        default=NarrativeOutcome.INCOMPLETE,
        description="How this episode resolved."
    )
    created_at: datetime = Field(default_factory=datetime.now)


# === JOURNEY ARC ===

class JourneyArc(BaseModel):
    """Narrative about a component milestone — aggregates episodes.

    A journey covers the full arc of building/fixing/understanding
    one component or feature. Multiple episodes compose into a journey
    when they share a component focus.

    Maps to JourneyCore (core.py) for the content arc:
    - JourneyCore.status_quo = where the component started
    - JourneyCore.obstacle = what blocked progress
    - JourneyCore.overcome = the breakthrough
    - JourneyCore.accomplishment = what was achieved
    - JourneyCore.the_boon = transferable insight
    """
    journey_id: str = Field(
        ..., description="Unique identifier. Format: Journey_{component}_{date}"
    )
    title: str = Field(
        ..., description="Journey title."
    )
    component_name: str = Field(
        ..., description="Name of the component/feature this journey covers."
    )

    # Composition
    episode_ids: List[str] = Field(
        default_factory=list,
        description="Ordered list of episode IDs composing this journey."
    )

    # Synthesis
    summary: str = Field(
        ..., description="Synthesized narrative across all episodes."
    )
    key_learnings: List[str] = Field(
        default_factory=list,
        description="Important insights distilled from the journey."
    )
    concepts: List[str] = Field(
        default_factory=list,
        description="CartON concept names relevant to this journey."
    )

    # Outcome
    outcome: NarrativeOutcome = Field(
        default=NarrativeOutcome.INCOMPLETE,
        description="How this journey resolved."
    )
    created_at: datetime = Field(default_factory=datetime.now)


# === EPIC ARC ===

class EpicArc(BaseModel):
    """Narrative about a module milestone — aggregates journeys.

    An epic covers a major module or system. Multiple journeys compose
    into an epic when they belong to the same module scope.

    This is the highest narrative level before autobiography.
    """
    epic_id: str = Field(
        ..., description="Unique identifier. Format: Epic_{module}_{date}"
    )
    title: str = Field(
        ..., description="Epic title."
    )
    module_name: str = Field(
        ..., description="Name of the module/system this epic covers."
    )

    # Composition
    journey_ids: List[str] = Field(
        default_factory=list,
        description="Ordered list of journey IDs composing this epic."
    )

    # Synthesis
    summary: str = Field(
        ..., description="Synthesized narrative across all journeys."
    )
    key_learnings: List[str] = Field(
        default_factory=list,
        description="Strategic insights from the epic."
    )
    concepts: List[str] = Field(
        default_factory=list,
        description="CartON concept names relevant to this epic."
    )

    # Outcome
    outcome: NarrativeOutcome = Field(
        default=NarrativeOutcome.INCOMPLETE,
        description="How this epic resolved."
    )
    created_at: datetime = Field(default_factory=datetime.now)
