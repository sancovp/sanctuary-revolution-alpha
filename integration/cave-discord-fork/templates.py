"""
CAVE Discord Templates - Journey documentation that transmits frequency, not mechanics.

These templates turn real journeys into "quotidian but polished" posts.
Structure invisible. Voice natural. Mechanics in the field descriptions.
"""

from typing import Optional, List
from pydantic import Field
from pydantic_stack_core import RenderablePiece, MetaStack


class JourneyPost(RenderablePiece):
    """
    A single journey post - the atomic unit of CAVE content.

    Not obviously a formula. Looks like someone just telling their story.
    The mechanics are in the field descriptions to guide correct filling.

    The arc: |IgnorantState| -> |Obstacle| -> |Overcome| -> |WiseState|
    Where WiseState = opposite of IgnorantState AS A FEELING, WITH PROOF.
    """

    journey_name: str = Field(
        description="Name of the journey. Short, evocative. e.g., 'Learning MCP Architecture'"
    )

    status_quo: str = Field(
        description="'I was...' - Inside the ignorant state, not describing it. "
                    "Reader should see themselves. Create recognition."
    )

    obstacle: str = Field(
        description="'I identified...when...' - The specific blocker and the moment "
                    "you recognized it. Concrete, not vague."
    )

    overcome: str = Field(
        description="'I finally...and tried...' - The shift in understanding + "
                    "what you actually did. The pivot point."
    )

    accomplishment: str = Field(
        description="'...happened...and now...' - The result. "
                    "MUST be: opposite of status_quo AS A FEELING, WITH PROOF. "
                    "Numbers, timeline, social validation if possible."
    )

    # Optional: link to the actual flights/resources
    flights_link: Optional[str] = Field(
        default=None,
        description="Link to the flights/resources that enabled this journey. "
                    "Invitation, not pitch."
    )

    def render(self) -> str:
        """Render as natural Discord markdown. Structure disappears."""
        output = f"""**Journey: {self.journey_name}**

**Status Quo:** {self.status_quo}

**Obstacle:** {self.obstacle}

**Overcome:** {self.overcome}

**Accomplishment:** {self.accomplishment}"""

        if self.flights_link:
            output += f"\n\n---\n*The journey is here if you want it: {self.flights_link}*"

        return output


class DomainOverview(RenderablePiece):
    """
    Overview post for a domain (PAIAB, SANCTUM, CAVE).

    Sets the context: what this domain is about, what journeys live here,
    what frequency you're stepping into.
    """

    domain_name: str = Field(
        description="PAIAB, SANCTUM, or CAVE"
    )

    domain_essence: str = Field(
        description="What this domain IS. Not what it contains - what frequency it represents. "
                    "e.g., 'PAIAB is where we build AI that builds AI.'"
    )

    what_lives_here: str = Field(
        description="Brief description of the journeys in this domain. "
                    "e.g., 'Journeys about MCP development, agent architecture, compound intelligence.'"
    )

    def render(self) -> str:
        return f"""# {self.domain_name}

{self.domain_essence}

**What lives here:** {self.what_lives_here}

---
*Browse the journeys below. Each one is real. Each one is copyable.*"""


class JourneyBlog(RenderablePiece):
    """
    Long form journey content - for blogs and YouTube scripts.

    AIDA within AIDA: Each section is its own AIDA cycle.
    The whole piece is also an AIDA cycle.

    This IS the YouTube script (written form).
    Video = this read aloud + demos injected.
    """

    # === SECTION 1: HOOK (Attention) ===
    hook_attention: str = Field(
        description="AIDA-Attention: Intriguing statement or question. "
                    "Something that makes them NEED to keep reading. "
                    "Surprising fact, counterintuitive claim, or recognition trigger."
    )
    hook_interest: str = Field(
        description="AIDA-Interest: Hint at what they'll learn or gain. "
                    "Build curiosity without revealing everything."
    )
    hook_desire: str = Field(
        description="AIDA-Desire: Promise valuable insights. "
                    "What transformation or knowledge awaits?"
    )
    hook_action: str = Field(
        description="AIDA-Action: Encourage them to keep reading/watching. "
                    "Natural transition into the content."
    )

    # === SECTION 2: TOPIC INTRO (Interest) ===
    topic_attention: str = Field(
        description="AIDA-Attention: Reiterate main topic to refocus. "
                    "What is this actually about?"
    )
    topic_interest: str = Field(
        description="AIDA-Interest: Interesting angle or aspect. "
                    "Why is this different from what they've heard before?"
    )
    topic_desire: str = Field(
        description="AIDA-Desire: Benefits/value they'll get. "
                    "What will they be able to DO after this?"
    )
    topic_action: str = Field(
        description="AIDA-Action: Stay tuned for insights. "
                    "Transition to personal connection."
    )

    # === SECTION 3: PERSONAL UPDATE (Connection) ===
    personal_attention: str = Field(
        description="AIDA-Attention: Something unexpected from your life/journey. "
                    "Where were YOU when this happened?"
    )
    personal_interest: str = Field(
        description="AIDA-Interest: Details that engage curiosity. "
                    "The specific situation, the feeling, the moment."
    )
    personal_desire: str = Field(
        description="AIDA-Desire: How your experience benefits them. "
                    "'I went through this so you don't have to' energy."
    )
    personal_action: str = Field(
        description="AIDA-Action: Stay connected with the journey. "
                    "Transition to main content."
    )

    # === SECTION 3a: AD INSERT (Optional) ===
    ad_content: Optional[str] = Field(
        default=None,
        description="Direct marketing AD. Lead gen -> CTA. "
                    "Can be Patreon plug, course mention, etc. "
                    "Should feel natural, not jarring."
    )

    # === SECTION 4: MAIN CONTENT (Desire - the meat) ===
    main_attention: str = Field(
        description="AIDA-Attention: Compelling statement/fact about the topic. "
                    "The 'here's the thing' moment."
    )
    main_interest: str = Field(
        description="AIDA-Interest: Interesting details and insights. "
                    "The actual content, the explanation, the how."
    )
    main_desire: str = Field(
        description="AIDA-Desire: How understanding this benefits them. "
                    "What can they DO with this knowledge?"
    )
    main_action: str = Field(
        description="AIDA-Action: Encourage application or reflection. "
                    "Transition to show and tell."
    )

    # === SECTION 5: SHOW AND TELL (Desire - demo) ===
    demo_attention: str = Field(
        description="AIDA-Attention: Visual/concrete example intro. "
                    "'Let me show you what this looks like.'"
    )
    demo_interest: str = Field(
        description="AIDA-Interest: Explain what you're showing and why. "
                    "Walk through the example."
    )
    demo_desire: str = Field(
        description="AIDA-Desire: How this demo benefits/interests them. "
                    "'You could do this for YOUR thing.'"
    )
    demo_action: str = Field(
        description="AIDA-Action: Encourage them to try it. "
                    "Transition to discussion."
    )

    # === SECTION 6: DISCUSSION (Engagement) ===
    discuss_attention: str = Field(
        description="AIDA-Attention: Thought-provoking question. "
                    "Something that makes them WANT to respond."
    )
    discuss_interest: str = Field(
        description="AIDA-Interest: Why this discussion matters. "
                    "What's at stake?"
    )
    discuss_desire: str = Field(
        description="AIDA-Desire: How participating benefits them. "
                    "Community, learning, connection."
    )
    discuss_action: str = Field(
        description="AIDA-Action: Share thoughts in comments. "
                    "Specific prompt for engagement."
    )

    # === SECTION 7: ANNOUNCEMENTS (Optional) ===
    announce_content: Optional[str] = Field(
        default=None,
        description="News, updates, upcoming things. "
                    "What's next on the journey?"
    )

    # === SECTION 8: CTA (Action) ===
    cta_attention: str = Field(
        description="AIDA-Attention: Importance of their action. "
                    "Why like/subscribe/share matters."
    )
    cta_interest: str = Field(
        description="AIDA-Interest: How their action contributes. "
                    "To the community, to the mission."
    )
    cta_desire: str = Field(
        description="AIDA-Desire: Urgency or exclusivity. "
                    "Why NOW? What will they miss?"
    )
    cta_action: str = Field(
        description="AIDA-Action: Clear specific action. "
                    "What exactly should they do? Link to what?"
    )

    # Metadata
    journey_name: str = Field(description="Name of the journey this blog covers")

    def render(self) -> str:
        """Render as blog post / YouTube script."""
        sections = []

        # HOOK
        sections.append(f"""## The Hook

{self.hook_attention}

{self.hook_interest}

{self.hook_desire}

{self.hook_action}
""")

        # TOPIC INTRO
        sections.append(f"""## What This Is About

{self.topic_attention}

{self.topic_interest}

{self.topic_desire}

{self.topic_action}
""")

        # PERSONAL
        sections.append(f"""## My Journey With This

{self.personal_attention}

{self.personal_interest}

{self.personal_desire}

{self.personal_action}
""")

        # AD (optional)
        if self.ad_content:
            sections.append(f"""---

{self.ad_content}

---
""")

        # MAIN CONTENT
        sections.append(f"""## The Core Insight

{self.main_attention}

{self.main_interest}

{self.main_desire}

{self.main_action}
""")

        # DEMO
        sections.append(f"""## Let Me Show You

{self.demo_attention}

{self.demo_interest}

{self.demo_desire}

{self.demo_action}
""")

        # DISCUSSION
        sections.append(f"""## Let's Talk About This

{self.discuss_attention}

{self.discuss_interest}

{self.discuss_desire}

{self.discuss_action}
""")

        # ANNOUNCEMENTS (optional)
        if self.announce_content:
            sections.append(f"""## What's Next

{self.announce_content}
""")

        # CTA
        sections.append(f"""## Take Action

{self.cta_attention}

{self.cta_interest}

{self.cta_desire}

{self.cta_action}
""")

        return f"# {self.journey_name}\n\n" + "\n".join(sections)


class LinkedInPost(RenderablePiece):
    """
    LinkedIn post format - professional but personal.

    Voice: Thoughtful professional sharing a genuine insight.
    Not corporate. Not salesy. Just "here's something I learned."
    """

    hook: str = Field(
        description="Opening line that stops the scroll. "
                    "Pattern interrupt or counterintuitive statement. "
                    "LinkedIn loves 'I used to think X. Now I know Y.'"
    )

    story_brief: str = Field(
        description="2-3 sentences of the journey. "
                    "Problem → shift → result. Condensed but human."
    )

    insight: str = Field(
        description="The one takeaway. The boon. "
                    "What's the reframe? What did you learn?"
    )

    application: str = Field(
        description="How this applies to THEM. "
                    "'If you're dealing with X, try Y.' "
                    "Make it actionable for the reader."
    )

    cta: str = Field(
        description="Soft CTA. Question or invitation. "
                    "'What's your experience with this?' or "
                    "'Link to full breakdown in comments.'"
    )

    hashtags: Optional[List[str]] = Field(
        default=None,
        description="3-5 relevant hashtags. "
                    "#AI #Automation #ProductivityTips etc."
    )

    def render(self) -> str:
        """Render as LinkedIn post with line breaks for readability."""
        parts = [
            self.hook,
            "",
            self.story_brief,
            "",
            self.insight,
            "",
            self.application,
            "",
            self.cta
        ]

        if self.hashtags:
            parts.append("")
            parts.append(" ".join(f"#{tag}" for tag in self.hashtags))

        return "\n".join(parts)


class TwitterPostSet(RenderablePiece):
    """
    Twitter/X post set - hook tweet + media placeholder + reply with link.

    Format:
    - Main tweet: Hooky description (< 280 chars ideally)
    - Media: [GIF/VIDEO placeholder for demo]
    - Reply: Link + context
    """

    hook_tweet: str = Field(
        description="The main tweet. Punchy. < 280 chars ideal. "
                    "Pattern interrupt, surprising claim, or 'watch this' energy."
    )

    media_description: str = Field(
        description="Description of the GIF/video to attach. "
                    "What should the demo show? This guides capture."
    )

    reply_context: str = Field(
        description="Brief context for the reply. "
                    "What is this actually? 1-2 sentences."
    )

    reply_link: str = Field(
        description="Link to full content (blog, YouTube, etc.)"
    )

    reply_cta: str = Field(
        description="What action? 'Full breakdown here' or "
                    "'Thread on how I built this' etc."
    )

    def render(self) -> str:
        return f"""=== MAIN TWEET ===
{self.hook_tweet}

[ATTACH: {self.media_description}]

=== REPLY ===
{self.reply_context}

{self.reply_cta}: {self.reply_link}"""


class ContentSuite(MetaStack):
    """
    Full content suite from a single journey.

    One journey → all platform formats.
    Same source data, different resolutions and voices.
    """

    journey_name: str = Field(description="Name of the journey")

    discord_post: JourneyPost = Field(description="Short form for Discord")
    blog_post: JourneyBlog = Field(description="Long form for blog/YouTube")
    linkedin_post: LinkedInPost = Field(description="Professional network")
    twitter_set: TwitterPostSet = Field(description="Twitter hook + reply")

    def render(self) -> str:
        """Render all formats with separators."""
        return f"""# Content Suite: {self.journey_name}

{'='*60}
## DISCORD POST
{'='*60}

{self.discord_post.render()}

{'='*60}
## LINKEDIN POST
{'='*60}

{self.linkedin_post.render()}

{'='*60}
## TWITTER SET
{'='*60}

{self.twitter_set.render()}

{'='*60}
## BLOG/YOUTUBE (abbreviated - see full render)
{'='*60}

[See JourneyBlog.render() for full content]
Title: {self.blog_post.journey_name}
Hook: {self.blog_post.hook_attention}
"""


class ChannelStructure(MetaStack):
    """
    The fractal structure: DOMAIN -> overview, journeys, frameworks

    This defines what gets created when we stamp out a domain.
    """

    domain: str = Field(description="PAIAB, SANCTUM, or CAVE")

    overview: DomainOverview = Field(
        description="The overview post for #overview channel"
    )

    journeys: List[JourneyPost] = Field(
        default_factory=list,
        description="Journey posts for #journeys channel"
    )

    # frameworks would be paywalled content - separate template

    def render(self) -> str:
        """Render the full domain structure."""
        parts = [
            f"=== {self.domain} ===\n",
            "## #overview\n",
            self.overview.render(),
            "\n\n## #journeys\n"
        ]

        for journey in self.journeys:
            parts.append(journey.render())
            parts.append("\n\n---\n\n")

        return "".join(parts)
