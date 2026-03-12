"""
Odyssey System — PBML cycle models mapping 1:1 to GIINT.

The Odyssey system orchestrates continuous improvement across project
iterations using Plan-Build-Measure-Learn cycles.

Odyssey → GIINT mapping:
- Project → GIINT Project
- Module → GIINT Feature
- Component → GIINT Component
- Task → GIINT Task (Deliverable is implicit in Task completion)
- OdysseyPhase → L4 Phase (summarizer output)
- Iteration → Full PBML cycle
- Learning → CartON concept (extracted insight)
- MetaLearning → CartON collection (cross-iteration patterns)

Origin: Ported from /home/GOD/core/computer_use_demo/codebase_analyzer_system/odyssey_system.py
Changes: RegistryService → CartON, BaseHeavenAgentReplicant → SDNA, manual dict ops → Pydantic v2

Data flow:
- GIINT projects define the work structure
- Iterations execute PBML cycles against that structure
- Each phase produces episodes (via narrative_arc.py)
- Learnings extract patterns (via CartON)
- MetaLearnings aggregate cross-iteration insights
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# === ENUMS ===

class OdysseyPhaseType(str, Enum):
    """Phase types in the PBML cycle."""
    PLAN = "plan"
    BUILD = "build"
    MEASURE = "measure"
    LEARN = "learn"


class IterationOutcome(str, Enum):
    """Possible outcomes for an iteration."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    INCOMPLETE = "incomplete"


# === PROJECT STRUCTURE (maps to GIINT) ===

class Task(BaseModel):
    """A task in a project. Maps to GIINT Task."""
    name: str = Field(..., description="Task name.")
    description: str = Field(..., description="What needs to be done.")
    component: str = Field(
        ..., description="Component this task belongs to."
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other task names this depends on."
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Criteria for task completion."
    )


class Component(BaseModel):
    """A component in a project. Maps to GIINT Component."""
    name: str = Field(..., description="Component name.")
    description: str = Field(..., description="Component purpose.")
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other component names this depends on."
    )


class Module(BaseModel):
    """A module in a project. Maps to GIINT Feature."""
    name: str = Field(..., description="Module name.")
    description: str = Field(..., description="Module purpose.")
    components: List[str] = Field(
        default_factory=list,
        description="Component names in this module."
    )


class Project(BaseModel):
    """A complete project definition. Maps to GIINT Project."""
    name: str = Field(..., description="Project name.")
    description: str = Field(..., description="Project description.")
    modules: List[Module] = Field(default_factory=list)
    components: List[Component] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


# === PBML CYCLE ===

class OdysseyPhase(BaseModel):
    """One phase of the Plan-Build-Measure-Learn cycle.

    Each phase maps to L4 phase aggregations from the summarizer.
    Episodes are constructed from phase output (via narrative_arc.py).
    """
    phase_id: str = Field(
        ..., description="Unique identifier."
    )
    phase_type: OdysseyPhaseType = Field(
        ..., description="Which PBML phase."
    )
    episode_ids: List[str] = Field(
        default_factory=list,
        description="Episode IDs created during this phase."
    )
    summary: str = Field(
        default="",
        description="Phase summary."
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Outputs produced during this phase."
    )
    concept_focus: List[str] = Field(
        default_factory=list,
        description="CartON concepts this phase focuses on."
    )
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class Iteration(BaseModel):
    """One complete PBML cycle attempt.

    An iteration contains up to 4 phases (PLAN → BUILD → MEASURE → LEARN).
    Each phase produces episodes. Learnings are extracted at the end.
    """
    iteration_id: str = Field(
        ..., description="Unique identifier."
    )
    project_name: str = Field(
        ..., description="Name of the project."
    )
    iteration_number: int = Field(
        ..., description="Sequence number."
    )
    phases: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps phase_type → phase_id."
    )
    outcome: IterationOutcome = Field(
        default=IterationOutcome.INCOMPLETE,
        description="How this iteration resolved."
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics."
    )
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# === LEARNING SYSTEM ===

class Learning(BaseModel):
    """A learning extracted from iterations.

    Learnings become CartON concepts with proper typing.
    They feed back into future iterations via the LEARN phase.
    """
    learning_id: str = Field(
        ..., description="Unique identifier."
    )
    content: str = Field(
        ..., description="The learning content — what was discovered."
    )
    concepts: List[str] = Field(
        default_factory=list,
        description="CartON concept names this learning relates to."
    )
    iteration_ids: List[str] = Field(
        default_factory=list,
        description="Iterations this learning came from."
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence score (0-1). Higher = more iterations confirm it."
    )
    created_at: datetime = Field(default_factory=datetime.now)


class MetaLearning(BaseModel):
    """Cross-iteration learning — patterns across multiple iterations.

    MetaLearnings become CartON collections grouping related Learnings.
    They represent higher-order insights about the project itself.
    """
    meta_learning_id: str = Field(
        ..., description="Unique identifier."
    )
    project_name: str = Field(
        ..., description="Project this meta-learning is for."
    )
    iteration_ids: List[str] = Field(
        default_factory=list,
        description="Iterations analyzed."
    )
    learning_ids: List[str] = Field(
        default_factory=list,
        description="Learnings discovered."
    )
    patterns: Dict[str, str] = Field(
        default_factory=dict,
        description="Discovered patterns. Maps pattern_name → description."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations."
    )
    created_at: datetime = Field(default_factory=datetime.now)
