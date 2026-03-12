"""SANCTUM Builder Models - Life architecture system.

[SANCTUM] = Life architecture mini-game in Sanctuary Revolution.
Integrates with:
- sanctuary-system myth layer (MVS, VEC, SanctuaryJourney)
- life_architecture_app infrastructure (LifePlan, DailyLog, schedules)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from datetime import datetime, time, date as dt_date

# Import from sanctuary-system myth layer
from sanctuary_system import (
    MVS,
    VEC,
    SanctuaryJourney,
    SanctuaryDegree,
    WisdomMaverickState,
)

# Import from life_architecture_app infrastructure
from life_app.models import LifePlan, DailyLog, Experiment
from life_app.schedules import DaySchedule, WeekSchedule, SchedulePattern, ScheduleItem


class LifeDomain(str, Enum):
    """Life domains in SANCTUM."""
    HEALTH = "health"
    WEALTH = "wealth"
    RELATIONSHIPS = "relationships"
    PURPOSE = "purpose"
    GROWTH = "growth"
    ENVIRONMENT = "environment"


class RitualFrequency(str, Enum):
    """Ritual frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RitualSpec(BaseModel):
    """A ritual/routine in SANCTUM."""
    name: str
    description: str
    domain: LifeDomain
    frequency: RitualFrequency = RitualFrequency.DAILY
    time_of_day: Optional[str] = None  # e.g., "morning", "evening", "06:00"
    duration_minutes: int = 15
    active: bool = True
    streak: int = 0  # Current streak
    created: datetime = Field(default_factory=datetime.now)


class GoalSpec(BaseModel):
    """A goal in SANCTUM."""
    name: str
    description: str
    domain: LifeDomain
    target_date: Optional[datetime] = None
    progress: int = 0  # 0-100
    milestones: List[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=datetime.now)


class BoundarySpec(BaseModel):
    """A boundary/constraint in SANCTUM."""
    name: str
    description: str
    domain: LifeDomain
    rule: str  # The actual constraint
    active: bool = True


class GEARScore(BaseModel):
    """[GEAR] Growth-Experience-Awareness-Reality score.

    Derived from DailyLog completion rates against LifePlan goals.
    - G (Growth): Progress toward goals over time
    - E (Experience): Daily execution (DailyLog vs LifePlan)
    - A (Awareness): Mood/energy/focus self-reporting
    - R (Reality): Schedule adherence (actual vs planned)
    """
    growth: int = Field(default=0, ge=0, le=100, description="Growth score 0-100")
    experience: int = Field(default=0, ge=0, le=100, description="Experience score 0-100")
    awareness: int = Field(default=0, ge=0, le=100, description="Awareness score 0-100")
    reality: int = Field(default=0, ge=0, le=100, description="Reality score 0-100")

    @computed_field
    @property
    def total(self) -> int:
        """Total GEAR score (average of all components)."""
        return (self.growth + self.experience + self.awareness + self.reality) // 4


class ExperienceEntry(BaseModel):
    """[EXPERIENCE] Single day's experience tracking.

    Wraps DailyLog with Sanctuary vocabulary and GEAR derivation.
    """
    date: dt_date
    daily_log_ref: Optional[str] = None  # Reference to DailyLog user_id+date

    # Derived GEAR for this day
    gear: GEARScore = Field(default_factory=GEARScore)

    # Sanctuary annotations
    rituals_completed: List[str] = Field(default_factory=list)
    boundaries_held: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class SANCTUM(BaseModel):
    """[SANCTUM] Life architecture specification.

    Integrates with sanctuary-system:
    - MVS (Minimum Viable Sanctuary) = rituals + boundaries + structures
    - VEC (Victory-Everything Chain) = journey + MVS + agent
    - SanctuaryJourney = transformation path
    """
    name: str
    description: str

    # Components (local tracking)
    rituals: List[RitualSpec] = Field(default_factory=list)
    goals: List[GoalSpec] = Field(default_factory=list)
    boundaries: List[BoundarySpec] = Field(default_factory=list)

    # Sanctuary-system integration
    mvs_name: Optional[str] = None  # Reference to MVS in sanctuary-system
    journey_name: Optional[str] = None  # Reference to SanctuaryJourney
    vec_name: Optional[str] = None  # Reference to VEC

    # life_architecture_app integration
    life_plan_user_id: Optional[str] = None  # Reference to LifePlan in life_app
    experience_log: List[ExperienceEntry] = Field(default_factory=list)  # GEAR tracking
    current_gear: GEARScore = Field(default_factory=GEARScore)  # Rolling GEAR score

    # Sanctuary state
    sanctuary_degree: SanctuaryDegree = SanctuaryDegree.OVP

    # Domain scores (0-100)
    domain_scores: Dict[str, int] = Field(default_factory=lambda: {
        d.value: 0 for d in LifeDomain
    })

    # Meta
    created: datetime = Field(default_factory=datetime.now)
    updated: Optional[datetime] = None

    @computed_field
    @property
    def overall_score(self) -> int:
        """Average across all domains."""
        if not self.domain_scores:
            return 0
        return sum(self.domain_scores.values()) // len(self.domain_scores)

    @computed_field
    @property
    def is_complete(self) -> bool:
        """SANCTUM complete when all domains >= 80."""
        return all(score >= 80 for score in self.domain_scores.values())
