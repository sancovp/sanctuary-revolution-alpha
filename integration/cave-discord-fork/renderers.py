"""
CAVE Renderers - Platform-specific templates that derive from JourneyCore.

Each renderer has a .from_core() method that takes a JourneyCore
and produces platform-appropriate output.
"""

from typing import Optional, List
from pydantic import Field
from pydantic_stack_core import RenderablePiece
from core import JourneyCore


class DiscordJourneyPost(RenderablePiece):
    """Short form for Discord #journeys channel."""

    journey_name: str
    status_quo: str
    obstacle: str
    overcome: str
    accomplishment: str
    links_section: str = ""

    @classmethod
    def from_core(cls, core: JourneyCore) -> "DiscordJourneyPost":
        return cls(
            journey_name=core.journey_name,
            status_quo=core.status_quo,
            obstacle=core.obstacle,
            overcome=core.overcome,
            accomplishment=core.accomplishment,
            links_section=core.links_section("discord")
        )

    def render(self) -> str:
        output = f"""**Journey: {self.journey_name}**

**Status Quo:** {self.status_quo}

**Obstacle:** {self.obstacle}

**Overcome:** {self.overcome}

**Accomplishment:** {self.accomplishment}"""

        if self.links_section:
            output += f"\n\n---\n{self.links_section}"

        return output


class LinkedInPost(RenderablePiece):
    """Professional network post."""

    hook: str
    story_brief: str
    insight: str
    application: str
    cta: str
    hashtags: List[str] = []

    @classmethod
    def from_core(cls, core: JourneyCore) -> "LinkedInPost":
        # Synthesize LinkedIn-appropriate content from core
        hook = f"I used to struggle with {core.status_quo.split()[2:6]}... Now everything's different."
        story_brief = f"{core.status_quo} {core.obstacle} Then: {core.overcome}"

        return cls(
            hook=hook,
            story_brief=story_brief,
            insight=core.the_boon,
            application=core.universal_application or f"If you're facing similar challenges, this might help.",
            cta="What's been your experience with this? Drop a comment.",
            hashtags=core.hashtags
        )

    def render(self) -> str:
        parts = [
            self.hook, "",
            self.story_brief, "",
            self.insight, "",
            self.application, "",
            self.cta
        ]
        if self.hashtags:
            parts.extend(["", " ".join(f"#{tag}" for tag in self.hashtags)])
        return "\n".join(parts)


class TwitterPostSet(RenderablePiece):
    """Twitter hook + media + reply with link."""

    hook_tweet: str
    media_description: str
    reply_context: str
    reply_link: str

    @classmethod
    def from_core(cls, core: JourneyCore) -> "TwitterPostSet":
        return cls(
            hook_tweet=f"{core.the_boon}\n\nWatch what happens:",
            media_description=f"GIF/Video: {core.demo_description}",
            reply_context=f"Journey: {core.journey_name}. {core.accomplishment[:100]}...",
            reply_link=core.blog_url or core.youtube_url or "[LINK TBD]"
        )

    def render(self) -> str:
        return f"""=== MAIN TWEET ===
{self.hook_tweet}

[ATTACH: {self.media_description}]

=== REPLY ===
{self.reply_context}

Full breakdown: {self.reply_link}"""


class YouTubeDescription(RenderablePiece):
    """YouTube video description with all cross-links."""

    title: str
    hook: str
    summary: str
    timestamps: List[str] = []  # Optional chapter markers
    links_section: str
    hashtags: List[str] = []

    @classmethod
    def from_core(cls, core: JourneyCore) -> "YouTubeDescription":
        return cls(
            title=core.journey_name,
            hook=core.the_boon,
            summary=f"{core.status_quo} → {core.accomplishment}",
            links_section=core.links_section("youtube"),
            hashtags=core.hashtags
        )

    def render(self) -> str:
        parts = [
            self.hook,
            "",
            self.summary,
            "",
            "=" * 40,
            "LINKS",
            "=" * 40,
            self.links_section,
        ]

        if self.timestamps:
            parts.extend([
                "",
                "=" * 40,
                "TIMESTAMPS",
                "=" * 40,
                *self.timestamps
            ])

        if self.hashtags:
            parts.extend(["", " ".join(f"#{tag}" for tag in self.hashtags)])

        return "\n".join(parts)


class BlogPost(RenderablePiece):
    """
    Long form blog post / YouTube script.

    Simplified from the full AIDA-within-AIDA structure.
    Uses JourneyCore + expansion fields.
    """

    journey_name: str

    # Hook
    hook: str

    # Story
    status_quo: str
    obstacle: str
    overcome: str
    accomplishment: str

    # The boon
    the_boon: str

    # Demo
    demo_intro: str
    demo_description: str
    demo_payoff: str

    # Expansion
    why_this_matters: str
    universal_application: str

    # CTA
    cta: str

    # Links
    links_section: str

    # YouTube embed (optional)
    youtube_url: Optional[str] = None

    @classmethod
    def from_core(cls, core: JourneyCore) -> "BlogPost":
        return cls(
            journey_name=core.journey_name,
            hook=f"What if you could {core.accomplishment.split('now')[1].strip() if 'now' in core.accomplishment else core.accomplishment}?",
            status_quo=core.status_quo,
            obstacle=core.obstacle,
            overcome=core.overcome,
            accomplishment=core.accomplishment,
            the_boon=core.the_boon,
            demo_intro="Let me show you what this looks like in practice.",
            demo_description=core.demo_description,
            demo_payoff=core.universal_application or "You could do this for YOUR domain.",
            why_this_matters=core.why_this_matters or f"This is bigger than just {core.journey_name}.",
            universal_application=core.universal_application or "This pattern applies everywhere.",
            cta="If this helped, share it with someone who needs it.",
            links_section=core.links_section("blog"),
            youtube_url=core.youtube_url
        )

    def render(self) -> str:
        sections = [
            f"# {self.journey_name}",
            "",
            f"**{self.hook}**",
            "",
            "## The Story",
            "",
            self.status_quo,
            "",
            self.obstacle,
            "",
            self.overcome,
            "",
            f"**{self.accomplishment}**",
            "",
            "## The Key Insight",
            "",
            self.the_boon,
            "",
            "## Demo",
            "",
            self.demo_intro,
            "",
            f"*[{self.demo_description}]*",
        ]

        # YouTube embed if available
        if self.youtube_url:
            sections.extend([
                "",
                f"[![Watch the demo]({self.youtube_url})]({self.youtube_url})",
            ])

        sections.extend([
            "",
            self.demo_payoff,
            "",
            "## Why This Matters",
            "",
            self.why_this_matters,
            "",
            self.universal_application,
            "",
            "## Take Action",
            "",
            self.cta,
            "",
            "---",
            "",
            self.links_section
        ])

        return "\n".join(sections)


class ContentSuite(RenderablePiece):
    """
    All platform renders from a single JourneyCore.

    Convenience wrapper that generates everything at once.
    """

    core: JourneyCore

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_core(cls, core: JourneyCore) -> "ContentSuite":
        return cls(core=core)

    @property
    def discord(self) -> DiscordJourneyPost:
        return DiscordJourneyPost.from_core(self.core)

    @property
    def linkedin(self) -> LinkedInPost:
        return LinkedInPost.from_core(self.core)

    @property
    def twitter(self) -> TwitterPostSet:
        return TwitterPostSet.from_core(self.core)

    @property
    def youtube_desc(self) -> YouTubeDescription:
        return YouTubeDescription.from_core(self.core)

    @property
    def blog(self) -> BlogPost:
        return BlogPost.from_core(self.core)

    def render(self) -> str:
        """Render all formats."""
        return f"""# Content Suite: {self.core.journey_name}

{'='*60}
## DISCORD
{'='*60}

{self.discord.render()}

{'='*60}
## LINKEDIN
{'='*60}

{self.linkedin.render()}

{'='*60}
## TWITTER
{'='*60}

{self.twitter.render()}

{'='*60}
## YOUTUBE DESCRIPTION
{'='*60}

{self.youtube_desc.render()}

{'='*60}
## BLOG (abbreviated)
{'='*60}

{self.blog.render()[:500]}...

[Full blog: {len(self.blog.render())} chars]
"""

    def render_all(self) -> dict:
        """Return dict of all rendered content."""
        return {
            "discord": self.discord.render(),
            "linkedin": self.linkedin.render(),
            "twitter": self.twitter.render(),
            "youtube_description": self.youtube_desc.render(),
            "blog": self.blog.render()
        }
