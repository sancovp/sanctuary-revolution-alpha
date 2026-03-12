"""
CAVE Core - Single source of truth for journey data.

JourneyCore is THE model. Everything else derives from it.
Fill it once, render everywhere with correct cross-links.
"""

from typing import Optional, List, Literal, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from offer import GrandSlamOffer


class JourneyCore(BaseModel):
    """
    Single source of truth for ONE journey.

    Fill this ONCE. All platform templates derive from it.
    Links fill in progressively as you publish to each platform.
    """

    # === IDENTITY ===
    journey_name: str = Field(
        description="Name of the journey. Short, evocative."
    )
    domain: Literal["PAIAB", "SANCTUM", "CAVE"] = Field(
        description="Which domain this journey belongs to."
    )

    # === CORE CONTENT (the journey itself) ===
    status_quo: str = Field(
        description="'I was...' - Inside the ignorant state. "
                    "Reader should see themselves."
    )
    obstacle: str = Field(
        description="'I identified...when...' - The specific blocker "
                    "and the moment you recognized it."
    )
    overcome: str = Field(
        description="'I finally...and tried...' - The shift + what you did."
    )
    accomplishment: str = Field(
        description="'...happened...and now...' - Result as FEELING + PROOF. "
                    "Opposite of status_quo."
    )

    # === THE BOON (transferable insight) ===
    the_boon: str = Field(
        description="The ONE reframe/insight/key. What transfers. "
                    "Not the artifact - the understanding."
    )

    # === DEMO ===
    demo_description: str = Field(
        description="What to capture for the demo. "
                    "Specific enough to guide recording."
    )
    demo_video_path: Optional[str] = Field(
        default=None,
        description="Path to demo footage once recorded."
    )

    # === EXPANSION (for long form) ===
    why_this_matters: Optional[str] = Field(
        default=None,
        description="Meta-level: why this insight matters beyond this instance. "
                    "'That's how I became interested in...'"
    )
    universal_application: Optional[str] = Field(
        default=None,
        description="How this applies universally. "
                    "'You could do this for YOUR domain...'"
    )

    # === CROSS-LINKS (fill as you publish) ===
    blog_url: Optional[str] = Field(
        default=None,
        description="URL to published blog post."
    )
    youtube_url: Optional[str] = Field(
        default=None,
        description="URL to YouTube video."
    )
    github_url: Optional[str] = Field(
        default=None,
        description="URL to relevant GitHub repo/code."
    )
    website_url: Optional[str] = Field(
        default=None,
        description="URL to main website."
    )
    discord_channel: Optional[str] = Field(
        default=None,
        description="Discord channel where this was posted."
    )

    # === THE OFFER (shared across all content) ===
    # This is set at the module level, not per-journey
    # All journeys point to the SAME offer

    # === METADATA ===
    hashtags: List[str] = Field(
        default_factory=lambda: ["AI", "Automation"],
        description="Hashtags for social posts."
    )

    def links_section(self, platform: str = "youtube", offer_url: Optional[str] = None) -> str:
        """Generate links section for a given platform."""
        links = []

        if platform == "youtube":
            # YouTube description gets ALL links
            if self.blog_url:
                links.append(f"📝 Full blog post: {self.blog_url}")
            if self.github_url:
                links.append(f"💻 GitHub: {self.github_url}")
            if offer_url:
                links.append(f"🎁 Get the full system: {offer_url}")
            if self.website_url:
                links.append(f"🌐 Website: {self.website_url}")
            if self.discord_channel:
                links.append(f"💬 Discord: {self.discord_channel}")

        elif platform == "blog":
            # Blog links to video, offer, github
            if self.youtube_url:
                links.append(f"🎬 Watch the video: {self.youtube_url}")
            if offer_url:
                links.append(f"🎁 Get the full system: {offer_url}")
            if self.github_url:
                links.append(f"💻 Code: {self.github_url}")

        elif platform == "discord":
            # Discord links to blog
            if self.blog_url:
                links.append(f"Full breakdown: {self.blog_url}")

        elif platform == "twitter":
            # Twitter just needs the blog or youtube link
            if self.blog_url:
                links.append(self.blog_url)
            elif self.youtube_url:
                links.append(self.youtube_url)

        elif platform == "linkedin":
            # LinkedIn gets blog link in comments usually
            if self.blog_url:
                links.append(f"Link to full breakdown in first comment: {self.blog_url}")

        return "\n".join(links) if links else ""
