"""
Pydantic models for the Capability Predictor system.

These models define the input/output schema for capability prediction:
- Input: CapabilityObservation (list of plan steps)
- Output: CapabilityPrediction (predictions for each step with skills/tools)

The pattern follows the be_myself awareness model:
structured input → processing → guidance output
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _round_confidence(v: float) -> float:
    """Round confidence to 1 decimal place."""
    return round(v, 1)


# ============================================================================
# Input Models
# ============================================================================


class PlanStep(BaseModel):
    """A single step in the user's plan - structured for deductive matching."""

    step_number: int = Field(..., ge=1, description="Step number (1-indexed)")
    description: str = Field(
        ..., min_length=1, description="Natural language description of this step"
    )
    # Typed fields for deductive chain - ALL str (not enum) for flexibility
    # LLM generates values designed to match graph concepts
    # Missing concepts get JIT created, duplicates get tagged together over time
    deliverable: Optional[str] = Field(
        default=None,
        description="What this step produces (maps to INSTANTIATES query)"
    )
    action_type: Optional[str] = Field(
        default=None,
        description="Type of action: create, read, update, delete, transform, etc (maps to IS_A pattern)"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Domain context: PAIAB, CAVE, SANCTUM, etc (maps to PART_OF domain)"
    )
    requires: Optional[list[str]] = Field(
        default=None,
        description="What this step requires (maps to HAS dependencies)"
    )
    context_tags: Optional[list[str]] = Field(
        default=None,
        description="Additional filter tags (maps to IS_A filters)"
    )


class CapabilityObservation(BaseModel):
    """
    What you submit to get predictions.

    Contains the plan steps you want capability predictions for,
    plus optional context about the domain you're working in.

    Example:
        >>> obs = CapabilityObservation(
        ...     steps=[
        ...         PlanStep(step_number=1, description="Plan the project structure"),
        ...         PlanStep(step_number=2, description="Implement the core logic"),
        ...         PlanStep(step_number=3, description="Write tests"),
        ...     ],
        ...     context_domain="PAIAB"
        ... )
    """

    steps: list[PlanStep] = Field(
        ..., min_length=1, description="List of plan steps to predict capabilities for"
    )
    context_domain: Optional[str] = Field(
        default=None,
        description="Domain context (e.g., 'PAIAB', 'CAVE', 'SANCTUM')",
    )


# ============================================================================
# Reasoning Chain Models
# ============================================================================


class ReasoningStep(BaseModel):
    """One step in the deductive reasoning chain."""

    layer: int = Field(..., description="Layer number in the chain")
    query_type: str = Field(
        ...,
        description="Relationship type used: EMBEDDING, IS_A, PART_OF, HAS, INSTANTIATES"
    )
    reasoning: str = Field(
        ...,
        description="Why this query was made: 'I need tools that produce X'"
    )
    query: str = Field(..., description="The semantic query constructed")
    results: list[str] = Field(default_factory=list, description="Concepts found")
    filtered_out: list[str] = Field(
        default_factory=list,
        description="Concepts removed by this filter"
    )


class ReasoningChain(BaseModel):
    """Full reasoning chain for a prediction."""

    steps: list[ReasoningStep] = Field(default_factory=list)
    seed_concepts: list[str] = Field(
        default_factory=list,
        description="Initial concepts from embedding search"
    )
    expanded_concepts: list[str] = Field(
        default_factory=list,
        description="Concepts discovered through deduction"
    )
    final_concepts: list[str] = Field(
        default_factory=list,
        description="Concepts after all filtering"
    )

    def format(self) -> str:
        """Human-readable reasoning chain."""
        lines = ["Reasoning Chain:"]
        lines.append(f"  Seeds: {self.seed_concepts}")
        for step in self.steps:
            lines.append(f"  L{step.layer} [{step.query_type}]: {step.reasoning}")
            lines.append(f"       → {step.results}")
            if step.filtered_out:
                lines.append(f"       ✂ filtered: {step.filtered_out}")
        lines.append(f"  Expanded: {self.expanded_concepts}")
        lines.append(f"  Final: {self.final_concepts}")
        return "\n".join(lines)


REWEIGHT_HINT = """
💡 Re-weight predictions by adding relationships to *graph concepts:
   Example: Toolgraph_Create_Skill IS_A High_Priority_For_Skill_Work
   System re-indexes on relationship update. Use IS_A, PART_OF, HAS, INSTANTIATES.
""".strip()


# ============================================================================
# Output Models - Skill Predictions
# ============================================================================


class PredictedSkill(BaseModel):
    """A predicted skill with confidence and hierarchical context."""

    name: str = Field(..., description="Skill name")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    skillset: Optional[str] = Field(
        default=None, description="Parent skillset if any"
    )
    domain: str = Field(..., description="Domain this skill belongs to")
    category: Optional[str] = Field(
        default=None,
        description="Skill category (understand, preflight, single_turn_process)",
    )

    _round = field_validator("confidence", mode="after")(_round_confidence)


class PredictedSkillset(BaseModel):
    """Aggregated skillset containing multiple skills."""

    name: str = Field(..., description="Skillset name")
    domain: str = Field(..., description="Domain this skillset belongs to")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated confidence"
    )
    skills: list[PredictedSkill] = Field(
        default_factory=list, description="Skills in this skillset"
    )

    _round = field_validator("confidence", mode="after")(_round_confidence)


class PredictedSkillDomain(BaseModel):
    """Aggregated domain with skillsets and orphan skills."""

    name: str = Field(..., description="Domain name")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated confidence"
    )
    skillsets: list[PredictedSkillset] = Field(
        default_factory=list, description="Skillsets in this domain"
    )
    orphan_skills: list[PredictedSkill] = Field(
        default_factory=list, description="Skills not in any skillset"
    )

    _round = field_validator("confidence", mode="after")(_round_confidence)


# ============================================================================
# Output Models - Tool Predictions
# ============================================================================


class PredictedTool(BaseModel):
    """A predicted tool with confidence and hierarchical context."""

    name: str = Field(..., description="Tool name")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    server: str = Field(..., description="MCP server this tool belongs to")
    domain: str = Field(..., description="Domain this tool belongs to")
    description: Optional[str] = Field(
        default=None, description="Brief description of what the tool does"
    )

    _round = field_validator("confidence", mode="after")(_round_confidence)


class PredictedServer(BaseModel):
    """Aggregated MCP server containing multiple tools."""

    name: str = Field(..., description="Server name")
    domain: str = Field(..., description="Domain this server belongs to")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated confidence"
    )
    tools: list[PredictedTool] = Field(
        default_factory=list, description="Tools in this server"
    )

    _round = field_validator("confidence", mode="after")(_round_confidence)


class PredictedToolDomain(BaseModel):
    """Aggregated domain with servers and orphan tools."""

    name: str = Field(..., description="Domain name")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated confidence"
    )
    servers: list[PredictedServer] = Field(
        default_factory=list, description="Servers in this domain"
    )
    orphan_tools: list[PredictedTool] = Field(
        default_factory=list, description="Tools not in any server"
    )

    _round = field_validator("confidence", mode="after")(_round_confidence)


# ============================================================================
# CartON Fallback (Stage 2)
# ============================================================================


class CartONFallbackResult(BaseModel):
    """Result from CartON scan when RAG Stage 1 returns no matches."""

    concepts: list[str] = Field(
        default_factory=list,
        description="Concepts found via CartON scan"
    )
    query: str = Field(..., description="Original query that triggered fallback")
    reasoning: str = Field(
        default="RAG Stage 1 returned no matches; CartON scan invoked",
        description="Why CartON fallback was triggered"
    )


# ============================================================================
# Combined Step Prediction
# ============================================================================


class StepPrediction(BaseModel):
    """Prediction for a single step - combines skill and tool predictions."""

    step_number: int = Field(..., ge=1, description="Step number (1-indexed)")
    description: str = Field(..., description="Step description")

    # Skill predictions (hierarchical)
    skill_domains: list[PredictedSkillDomain] = Field(
        default_factory=list,
        description="Skill predictions grouped by domain",
    )

    # Tool predictions (hierarchical)
    tool_domains: list[PredictedToolDomain] = Field(
        default_factory=list,
        description="Tool predictions grouped by domain",
    )

    # Summary
    top_skills: list[str] = Field(
        default_factory=list,
        description="Top recommended skill names (flattened)",
    )
    top_tools: list[str] = Field(
        default_factory=list,
        description="Top recommended tool names (flattened)",
    )

    # Stage 2 Fallback
    carton_fallback: Optional[CartONFallbackResult] = Field(
        default=None,
        description="CartON scan results when RAG Stage 1 found no matches"
    )


# ============================================================================
# Full Prediction Result
# ============================================================================


class CapabilityPrediction(BaseModel):
    """
    What you get back - complete prediction for all steps.

    Contains:
    - Per-step predictions with skills and tools
    - Overall domain summary
    - Recommendations text

    Example:
        >>> prediction.steps[0].top_skills
        ['starlog', 'waypoint', 'flight-config']
        >>> prediction.overall_domains
        ['navigation', 'building']
    """

    steps: list[StepPrediction] = Field(
        ..., description="Predictions for each step"
    )
    overall_domains: list[str] = Field(
        default_factory=list,
        description="Aggregated domains across all steps",
    )
    recommendations: str = Field(
        default="",
        description="Natural language recommendations based on predictions",
    )


# ============================================================================
# Usage Tracking Models (Phase 3)
# ============================================================================


class ActualUsage(BaseModel):
    """
    Record of what was actually used during execution.

    Used for comparing predictions vs actual usage to detect
    mismatches and improve the prediction model.
    """

    session_id: str = Field(..., description="Session identifier")
    step_description: str = Field(..., description="What step this was for")
    predicted_skills: list[str] = Field(
        default_factory=list, description="Skills we predicted"
    )
    predicted_tools: list[str] = Field(
        default_factory=list, description="Tools we predicted"
    )
    actual_skills: list[str] = Field(
        default_factory=list, description="Skills actually used"
    )
    actual_tools: list[str] = Field(
        default_factory=list, description="Tools actually used"
    )

    @property
    def skill_false_negatives(self) -> list[str]:
        """Skills used but not predicted (missed predictions)."""
        return [s for s in self.actual_skills if s not in self.predicted_skills]

    @property
    def skill_false_positives(self) -> list[str]:
        """Skills predicted but not used."""
        return [s for s in self.predicted_skills if s not in self.actual_skills]

    @property
    def skill_true_positives(self) -> list[str]:
        """Skills predicted and used."""
        return [s for s in self.predicted_skills if s in self.actual_skills]

    @property
    def tool_false_negatives(self) -> list[str]:
        """Tools used but not predicted (missed predictions)."""
        return [t for t in self.actual_tools if t not in self.predicted_tools]

    @property
    def tool_false_positives(self) -> list[str]:
        """Tools predicted but not used."""
        return [t for t in self.predicted_tools if t not in self.actual_tools]

    @property
    def tool_true_positives(self) -> list[str]:
        """Tools predicted and used."""
        return [t for t in self.predicted_tools if t in self.actual_tools]
