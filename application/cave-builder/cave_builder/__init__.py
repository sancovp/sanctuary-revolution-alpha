"""CAVE Builder - Business system construction with value ladders, content, and identity."""

from .models import (
    # Value Ladder
    ValueLadderStage, AIDAPhase, CustomerPhase, AIDAContent,
    RetargetingStrategy, Offer, ValueLadder,
    # Discord
    Domain, ChannelType, DiscordChannel, DiscordStructure,
    # Content
    BlogTemplate, LinkedInTemplate, TweetTemplate,
    YouTubeScript, YouTubeVideo,
    # Identity
    IdentityConstants,
    # Journey & Framework
    Journey, Framework,
    # Main
    CAVE,
)
from .core import CAVEBuilder

__all__ = [
    # Value Ladder
    "ValueLadderStage", "AIDAPhase", "CustomerPhase", "AIDAContent",
    "RetargetingStrategy", "Offer", "ValueLadder",
    # Discord
    "Domain", "ChannelType", "DiscordChannel", "DiscordStructure",
    # Content
    "BlogTemplate", "LinkedInTemplate", "TweetTemplate",
    "YouTubeScript", "YouTubeVideo",
    # Identity
    "IdentityConstants",
    # Journey & Framework
    "Journey", "Framework",
    # Main
    "CAVE", "CAVEBuilder",
]

__version__ = "0.2.0"
