"""CAVE Builder Models - Value ladder, Discord, Content, Identity."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from datetime import datetime


# =============================================================================
# VALUE LADDER (AIDA Fractal)
# =============================================================================

class ValueLadderStage(str, Enum):
    """Stages in the value ladder."""
    LEAD_MAGNET = "lead_magnet"      # LM - Free value
    TRIP_WIRE = "trip_wire"          # TW - Low-cost entry
    CORE_OFFERING = "core_offering"  # CO - Main product
    UPSELL = "upsell"                # US - Enhancement
    PREMIUM = "premium"              # PO - Top tier


class AIDAPhase(str, Enum):
    """AIDA cycle phases (recursive at each stage)."""
    ATTENTION = "attention"
    INTEREST = "interest"
    DESIRE = "desire"
    ACTION = "action"


class CustomerPhase(str, Enum):
    """Customer transformation phases."""
    VISITOR = "visitor"
    ENGAGED_LEAD = "engaged_lead"
    FIRST_TIME_CUSTOMER = "first_time_customer"
    CORE_CUSTOMER = "core_customer"
    REPEAT_CUSTOMER = "repeat_customer"
    BRAND_ADVOCATE = "brand_advocate"


class AIDAContent(BaseModel):
    """Content for each AIDA phase."""
    attention: str = ""   # What grabs attention
    interest: str = ""    # What builds interest
    desire: str = ""      # What creates desire
    action: str = ""      # What triggers action


class RetargetingStrategy(BaseModel):
    """Strategy for when conversion fails at a stage."""
    stage: ValueLadderStage
    analyze_behavior: str = ""      # Why didn't they convert?
    segment_approach: str = ""      # How to segment non-converters
    tailored_content: str = ""      # Custom content/reminders
    special_offer: str = ""         # Time-limited urgency
    feedback_loop: str = ""         # Learn from interactions


class Offer(BaseModel):
    """An offer in the value ladder."""
    name: str
    description: str
    stage: ValueLadderStage
    price: Optional[float] = None

    # AIDA content for this offer
    aida: AIDAContent = Field(default_factory=AIDAContent)

    # Transformation this offer provides
    from_phase: CustomerPhase = CustomerPhase.VISITOR
    to_phase: CustomerPhase = CustomerPhase.ENGAGED_LEAD

    # Storytelling
    story_element: str = ""        # Relatable story/case study
    emotional_hook: str = ""       # Emotional connection

    # Feedback
    feedback_mechanism: str = ""   # How to gather feedback

    # Retargeting if conversion fails
    retargeting: Optional[RetargetingStrategy] = None

    status: str = "draft"
    created: datetime = Field(default_factory=datetime.now)


class ValueLadder(BaseModel):
    """Complete value ladder with all stages."""
    name: str
    description: str
    offers: Dict[ValueLadderStage, Offer] = Field(default_factory=dict)

    @computed_field
    @property
    def stages_complete(self) -> int:
        return len(self.offers)


# =============================================================================
# DISCORD STRUCTURE
# =============================================================================

class Domain(str, Enum):
    """The three domains."""
    PAIAB = "paiab"      # AI agent building
    SANCTUM = "sanctum"  # Life architecture
    CAVE = "cave"        # Business/funnels


class ChannelType(str, Enum):
    """Types of Discord channels."""
    WELCOME = "welcome"
    OVERVIEW = "overview"
    JOURNEYS = "journeys"      # Public - ads
    FRAMEWORKS = "frameworks"  # Private - knowledge


class DiscordChannel(BaseModel):
    """A Discord channel."""
    name: str
    domain: Optional[Domain] = None
    channel_type: ChannelType
    is_private: bool = False
    description: str = ""


class DiscordStructure(BaseModel):
    """Complete Discord server structure."""
    server_name: str
    channels: List[DiscordChannel] = Field(default_factory=list)

    @classmethod
    def default_structure(cls, server_name: str) -> "DiscordStructure":
        """Create default 10-channel structure."""
        channels = [
            DiscordChannel(name="welcome", channel_type=ChannelType.WELCOME,
                          description="About info, onboarding"),
        ]
        for domain in Domain:
            channels.extend([
                DiscordChannel(name=f"{domain.value}-overview", domain=domain,
                              channel_type=ChannelType.OVERVIEW),
                DiscordChannel(name=f"{domain.value}-journeys", domain=domain,
                              channel_type=ChannelType.JOURNEYS,
                              description="Obstacle→solution stories = ADS"),
                DiscordChannel(name=f"{domain.value}-frameworks", domain=domain,
                              channel_type=ChannelType.FRAMEWORKS, is_private=True,
                              description="Extracted knowledge"),
            ])
        return cls(server_name=server_name, channels=channels)


# =============================================================================
# CONTENT TEMPLATES
# =============================================================================

class BlogTemplate(BaseModel):
    """Blog post template."""
    title: str
    hook: str = ""           # Opening hook
    body: str = ""           # Main content
    insights: List[str] = Field(default_factory=list)
    cta: str = ""            # Call to action (can use identity constant)
    tags: List[str] = Field(default_factory=list)
    source_journey: Optional[str] = None  # Link to journey that inspired it


class LinkedInTemplate(BaseModel):
    """LinkedIn post template."""
    hook: str = ""           # First line (most important)
    body: str = ""
    cta: str = ""
    hashtags: List[str] = Field(default_factory=list)
    source_journey: Optional[str] = None


class TweetTemplate(BaseModel):
    """Tweet template."""
    hook: str = ""           # Main tweet (max 280)
    thread: List[str] = Field(default_factory=list)  # Thread continuation
    source_journey: Optional[str] = None


class YouTubeScript(BaseModel):
    """YouTube video script structure."""
    intro: str = ""
    who_am_i: str = ""       # CONSTANT - set once via IdentityConstants
    body: str = ""
    demo: Optional[str] = None  # Optional, embedded in body
    insights: List[str] = Field(default_factory=list)
    cta: str = ""            # CONSTANT - set once via IdentityConstants


class YouTubeVideo(BaseModel):
    """YouTube video model."""
    title: str
    thumbnail_concept: str = ""  # Description of thumbnail
    script: YouTubeScript = Field(default_factory=YouTubeScript)
    source_journey: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# =============================================================================
# IDENTITY CONSTANTS
# =============================================================================

class IdentityConstants(BaseModel):
    """Set once, used everywhere."""
    who_am_i: str = ""           # YouTube, blog about, intros
    cta: str = ""                # Call to action across all content
    twitter_bio: str = ""
    linkedin_bio: str = ""
    about_short: str = ""        # One-liner
    about_long: str = ""         # Full about section

    # Brand
    brand_name: str = ""
    tagline: str = ""


# =============================================================================
# JOURNEY & FRAMEWORK
# =============================================================================

class Journey(BaseModel):
    """A documented journey = content = ad."""
    title: str
    domain: Domain

    # The hero's journey structure
    obstacle: str = ""           # What problem was faced
    solution: str = ""           # What solution was discovered
    transformation: str = ""     # What transformation resulted

    # Meta
    framework_extracted: Optional[str] = None  # Link to framework
    created: datetime = Field(default_factory=datetime.now)
    published: bool = False

    # Content generated from this journey
    blog: Optional[BlogTemplate] = None
    linkedin: Optional[LinkedInTemplate] = None
    tweet: Optional[TweetTemplate] = None
    youtube: Optional[YouTubeVideo] = None


class Framework(BaseModel):
    """Extracted knowledge pattern."""
    name: str
    domain: Domain

    problem_pattern: str = ""      # What recurring problem
    solution_pattern: str = ""     # Repeatable solution
    implementation: str = ""       # How to apply

    source_journeys: List[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=datetime.now)


# =============================================================================
# CAVE (ties everything together)
# =============================================================================

class CAVE(BaseModel):
    """CAVE - Complete business system."""
    name: str
    description: str

    # Identity
    identity: IdentityConstants = Field(default_factory=IdentityConstants)

    # Value ladder
    value_ladder: Optional[ValueLadder] = None

    # Discord
    discord: Optional[DiscordStructure] = None

    # Content
    journeys: List[Journey] = Field(default_factory=list)
    frameworks: List[Framework] = Field(default_factory=list)

    # Metrics
    mrr: float = 0.0
    subscribers: int = 0

    # Meta
    created: datetime = Field(default_factory=datetime.now)
    updated: Optional[datetime] = None

    @computed_field
    @property
    def is_complete(self) -> bool:
        """CAVE complete when has identity, value ladder, and generating revenue."""
        return (
            bool(self.identity.who_am_i) and
            bool(self.value_ladder) and
            self.mrr > 0
        )
