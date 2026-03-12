"""
CAVE Offer System - Grand Slam Offer creation and explanation.

The offer is explained via the value equation and structured
using the complete offer creation framework.

Note: Framework concepts derived from common direct response
marketing principles. Implementation is original.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ValueEquation(BaseModel):
    """
    The core equation: Value = (Dream Outcome × Likelihood) / (Time × Effort)

    Maximize the top, minimize the bottom.
    """

    dream_outcome: str = Field(
        description="What they GET. The transformation. The end state. "
                    "Make it vivid. Make it specific. What does their life look like?"
    )

    perceived_likelihood: str = Field(
        description="Why they'll succeed. Proof it works for people like THEM. "
                    "Testimonials, case studies, your own results. "
                    "'40+ documented journeys using this exact system.'"
    )

    time_to_result: str = Field(
        description="How FAST. Minimize perceived time. Show quick wins. "
                    "'First automation running in 30 minutes. Compounding by day 2.'"
    )

    effort_required: str = Field(
        description="How EASY. Minimize friction. "
                    "'Copy the templates. AI does the work. You just approve.'"
    )

    def render(self) -> str:
        return f"""{self.dream_outcome}

Why it works: {self.perceived_likelihood}

How fast: {self.time_to_result}

How easy: {self.effort_required}"""


class DeliveryMatrix(BaseModel):
    """
    How the offer is delivered - the mechanics.

    Each dimension affects perceived value differently.
    """

    group_ratio: Literal["one_to_one", "small_group", "one_to_many"] = Field(
        description="1-1 (highest touch), Small Group, One to Many (most scalable)"
    )

    effort_level: Literal["diy", "done_with_you", "done_for_you"] = Field(
        description="DIY (they do it), DWY (together), DFY (you do it for them)"
    )

    support_type: List[str] = Field(
        default_factory=lambda: ["discord", "email"],
        description="Support channels: discord, chat, email, phone, zoom, etc."
    )

    consumption_type: List[str] = Field(
        default_factory=lambda: ["recorded", "written"],
        description="How they consume: live, recorded, written, audio, video"
    )

    response_speed: str = Field(
        default="24-48 hours",
        description="How fast you respond: 24/7, same day, 24-48 hours, etc."
    )


class Bonus(BaseModel):
    """
    A bonus component - should solve a perceived problem.

    Bonuses should be MORE valuable than the core offer.
    Always give them a benefit-laden name.
    """

    name: str = Field(
        description="Benefit-laden name. Not 'PDF Guide' but "
                    "'The 30-Minute Context Setup Blueprint'"
    )

    what_it_is: str = Field(
        description="What they actually get."
    )

    problem_it_solves: str = Field(
        description="What perceived problem/objection this addresses. "
                    "'What if I don't know where to start?'"
    )

    benefit: str = Field(
        description="How it makes their experience faster/easier/better."
    )

    value_anchor: Optional[str] = Field(
        default=None,
        description="Price anchor. 'This alone sells for $X' or "
                    "'Took me 6 months to develop'"
    )

    def render(self) -> str:
        output = f"""**{self.name}**
{self.what_it_is}

Solves: {self.problem_it_solves}
Result: {self.benefit}"""
        if self.value_anchor:
            output += f"\n({self.value_anchor})"
        return output


class Guarantee(BaseModel):
    """
    Risk reversal - move the risk from them to you.
    """

    type: Literal[
        "unconditional",      # No questions asked
        "conditional",        # If you do X and don't get Y
        "anti",              # All sales final (for high-end)
        "performance"        # Pay per result
    ] = Field(description="Type of guarantee")

    statement: str = Field(
        description="The guarantee statement. "
                    "'If you don't X in Y time, we'll Z.'"
    )

    terms: Optional[str] = Field(
        default=None,
        description="Conditions for conditional guarantees. "
                    "Should match activation points in program."
    )


class Scarcity(BaseModel):
    """Real scarcity - capacity limits."""

    type: Literal["total_cap", "weekly_cap", "cohort_cap"] = Field(
        description="Type of scarcity"
    )

    limit: str = Field(
        description="The actual limit. 'Only 10 spots' or '5 per week'"
    )

    reason: str = Field(
        description="WHY the limit exists (must be real). "
                    "'Because I personally review every setup'"
    )


class Urgency(BaseModel):
    """Time pressure - why act now."""

    type: Literal["cohort", "seasonal", "bonus_expiring", "opportunity_shrinking"] = Field(
        description="Type of urgency"
    )

    statement: str = Field(
        description="The urgency statement. "
                    "'Next cohort starts Monday' or 'Bonus expires Friday'"
    )


class OfferName(BaseModel):
    """
    Benefit-Headline naming formula.

    Magnetic reason + Avatar + Goal + Interval + Container
    """

    magnetic_reason: str = Field(
        description="Why they should care. The hook."
    )

    avatar: str = Field(
        description="Who this is for. Their identity."
    )

    goal: str = Field(
        description="What they'll achieve."
    )

    time_interval: str = Field(
        description="In what timeframe. '6 weeks', '30 days', etc."
    )

    container_word: str = Field(
        description="What to call it. 'System', 'Blueprint', 'Method', 'Challenge'"
    )

    def render(self) -> str:
        return f"The {self.magnetic_reason} {self.container_word} for {self.avatar} to {self.goal} in {self.time_interval}"

    @property
    def short_name(self) -> str:
        return f"{self.magnetic_reason} {self.container_word}"


class ValueStackOffer(BaseModel):
    """
    The complete offer - everything stacked together.

    This is THE thing you're selling. One offer, everywhere.
    """

    # Identity
    name: OfferName
    url: str
    price: Optional[str] = None

    # Value Equation (the core pitch)
    value: ValueEquation

    # Delivery (how they get it)
    delivery: DeliveryMatrix

    # Core Components (the meat)
    core_components: List[str] = Field(
        description="3-5 core offer components. High value, mix of high/low cost."
    )

    # Bonuses (the sizzle)
    bonuses: List[Bonus] = Field(
        default_factory=list,
        description="1-10 bonuses. Each solves a perceived problem."
    )

    # Risk Reversal
    guarantee: Optional[Guarantee] = None

    # Scarcity & Urgency
    scarcity: Optional[Scarcity] = None
    urgency: Optional[Urgency] = None

    def render_pitch(self) -> str:
        """Render the offer pitch for content."""
        parts = [
            f"# {self.name.render()}",
            "",
            self.value.render(),
            "",
            "## What You Get:",
            ""
        ]

        for i, component in enumerate(self.core_components, 1):
            parts.append(f"{i}. {component}")

        if self.bonuses:
            parts.extend(["", "## Plus These Bonuses:", ""])
            for bonus in self.bonuses:
                parts.append(bonus.render())
                parts.append("")

        if self.guarantee:
            parts.extend([
                "## Guarantee:",
                self.guarantee.statement,
                ""
            ])

        if self.scarcity:
            parts.append(f"⚠️ {self.scarcity.limit} - {self.scarcity.reason}")

        if self.urgency:
            parts.append(f"⏰ {self.urgency.statement}")

        parts.extend(["", f"→ {self.url}"])

        return "\n".join(parts)

    def render_short_pitch(self) -> str:
        """Short pitch for CTAs."""
        return f"""{self.value.dream_outcome}

{self.value.perceived_likelihood}

{self.value.time_to_result}. {self.value.effort_required}

→ {self.url}"""

    def render_one_liner(self) -> str:
        """One line for quick CTAs."""
        return f"{self.name.short_name}: {self.value.dream_outcome} → {self.url}"
