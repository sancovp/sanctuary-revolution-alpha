"""
Fractal MetaStack - Generic fractal pattern template for recursive structures.

This module provides a reusable template for any fractal/recursive pattern:
- AIDA value ladders
- Hero's journey
- Product development cycles
- Learning pathways
- Any nested transformation sequence
"""

from typing import List, Optional, Dict, Tuple
from pydantic import Field
from .core import RenderablePiece, MetaStack


class FractalStage(RenderablePiece):
    """
    A single stage in a fractal pattern with substages.

    Example:
        FractalStage(
            emoji="🧲",
            name="Lead Magnet",
            substages={
                "Attention": "Free value offering grabs attention",
                "Interest": "Content quality piques interest",
                "Desire": "Recognition of additional needs",
                "Action": "Opt-in or registration"
            },
            transformation_from="Visitor",
            transformation_to="Engaged Lead",
            interaction="Downloadable content, webinar sign-up"
        )
    """

    emoji: str = Field(description="Emoji representing this stage")
    name: str = Field(description="Name of this stage")
    substages: Dict[str, str] = Field(description="Substages with descriptions")
    transformation_from: str = Field(description="Starting state")
    transformation_to: str = Field(description="Ending state")
    interaction: Optional[str] = Field(default=None, description="How users interact with this stage")

    def render(self) -> str:
        """Render this fractal stage as formatted text."""
        substage_lines = "\n  | -- ".join(
            f"{key}: {value}" for key, value in self.substages.items()
        )

        output = f"""[{self.emoji} {self.name}]
  | -- {substage_lines}
  |    |
  |    └-- [Transform]: {self.transformation_from} to {self.transformation_to}"""

        if self.interaction:
            output += f"\n  |    └-- [Interaction]: {self.interaction}"

        return output + "\n"


class FractalPattern(MetaStack):
    """
    Generic fractal pattern that can represent any recursive structure.

    This is the universal template for patterns like:
    - AIDA cycles in value ladder
    - Hero's journey stages
    - Product development phases
    - Learning pathways
    - ANY recursive transformation sequence

    Example:
        aida_ladder = FractalPattern(
            pattern_name="AIDA Value Ladder",
            pattern_description="Customer journey with AIDA cycles",
            stages=[lead_magnet_stage, trip_wire_stage, ...],
            meta_insight="Leverages ADHD trigger cycles...",
            failure_strategies={"Trip Wire": ["Analyze behavior", "Segment users"]},
            feedback_loops={"Lead Magnet": ("Survey", "Understand initial impression")},
            storytelling={"Lead Magnet": ("Success story", "Inspire hope")}
        )
    """

    pattern_name: str = Field(description="Name of this fractal pattern")
    pattern_description: str = Field(description="What this pattern represents")
    stages: List[FractalStage] = Field(description="Sequential stages in the pattern")

    # Optional meta-patterns
    meta_insight: Optional[str] = Field(
        default=None,
        description="Meta-level insight about how this pattern works (e.g., ADHD cycle explanation)"
    )
    failure_strategies: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Recovery strategies for each stage if unsuccessful"
    )
    feedback_loops: Optional[Dict[str, Tuple[str, str]]] = Field(
        default=None,
        description="Feedback mechanisms for each stage (mechanism, purpose)"
    )
    storytelling: Optional[Dict[str, Tuple[str, str]]] = Field(
        default=None,
        description="Storytelling elements for each stage (story, emotional connection)"
    )

    def render(self) -> str:
        """Render the complete fractal pattern with all optional sections."""
        sections = []

        # Header
        sections.append(f"# {self.pattern_name}\n")
        sections.append(f"{self.pattern_description}\n")

        # Render the fractal stages
        sections.append("\n## Pattern Structure\n")
        for i, stage in enumerate(self.stages):
            sections.append(stage.render())
            if i < len(self.stages) - 1:
                sections.append("  |\n  └--> ")

        # Meta-insight (like ADHD explanation)
        if self.meta_insight:
            sections.append(f"\n## Meta-Pattern Insight\n\n{self.meta_insight}\n")

        # Failure strategies
        if self.failure_strategies:
            sections.append("\n## Failure Recovery Strategies\n")
            for stage_name, strategies in self.failure_strategies.items():
                strategy_text = "\n            | -- ".join(
                    f"Stage {i+1}: {s}" for i, s in enumerate(strategies)
                )
                sections.append(f"""
[{stage_name} Unsuccessful]
      |
      └--> [🔙 Recovery Strategy]
            | -- {strategy_text}
""")

        # Feedback loops
        if self.feedback_loops:
            sections.append("\n## Feedback Loops\n")
            for stage_name, (mechanism, purpose) in self.feedback_loops.items():
                sections.append(f"""
**{stage_name}**
- **Mechanism**: {mechanism}
- **Purpose**: {purpose}
""")

        # Storytelling
        if self.storytelling:
            sections.append("\n## Storytelling Elements\n")
            for stage_name, (story, emotion) in self.storytelling.items():
                sections.append(f"""
**{stage_name}**
- **Story**: {story}
- **Emotional Connection**: {emotion}
""")

        return "".join(sections)
