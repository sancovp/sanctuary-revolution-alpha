"""Test the full system: ONE offer + multiple journeys → all platform content."""

from offer import (
    ValueStackOffer, ValueEquation, DeliveryMatrix, OfferName,
    Bonus, Guarantee, Scarcity, Urgency
)
from core import JourneyCore
from renderers import ContentSuite

# ============================================================
# THE OFFER (defined ONCE, used everywhere)
# ============================================================

SANCTUARY_OFFER = ValueStackOffer(
    name=OfferName(
        magnetic_reason="Compound Intelligence",
        avatar="developers and creators",
        goal="build AI systems that remember, learn, and automate your entire workflow",
        time_interval="30 days",
        container_word="System"
    ),
    url="https://patreon.com/sanctuary",
    price="$49/month",

    value=ValueEquation(
        dream_outcome="Your AI remembers everything. Your workflows run themselves. "
                      "You focus on creation while the system handles the rest.",

        perceived_likelihood="50+ documented journeys. The system that made this content. "
                             "Every template, every flight, every automation - proven and used daily.",

        time_to_result="First automation running in 30 minutes. Context compounding by day 2. "
                       "Full system operational within a week.",

        effort_required="Copy the templates. Follow the flights. The AI does the heavy lifting. "
                        "You just approve and iterate."
    ),

    delivery=DeliveryMatrix(
        group_ratio="one_to_many",
        effort_level="done_with_you",
        support_type=["discord", "github_issues"],
        consumption_type=["recorded", "written", "templates"],
        response_speed="24-48 hours in Discord"
    ),

    core_components=[
        "GNOSYS Plugin - The complete compound intelligence system",
        "Sanctuary Revolution - The game that teaches you to use it",
        "All Flight Configs - Replayable workflows for every domain",
        "All Skills - Context injection for every task",
        "All Templates - Content generation, MCP building, everything"
    ],

    bonuses=[
        Bonus(
            name="The 30-Minute Quick Start Flight",
            what_it_is="Step-by-step flight config to get your first automation running",
            problem_it_solves="'Where do I even start?'",
            benefit="Running automation in 30 minutes, not 30 days",
            value_anchor="The same onboarding I use with everyone"
        ),
        Bonus(
            name="Private Discord Access",
            what_it_is="Direct access to the community and me",
            problem_it_solves="'What if I get stuck?'",
            benefit="Answers within 24-48 hours, see what others are building",
            value_anchor="Where all the real conversations happen"
        ),
        Bonus(
            name="Weekly Journey Drops",
            what_it_is="New documented journeys every week as I complete them",
            problem_it_solves="'Will this keep up with AI changes?'",
            benefit="Always current, always expanding",
            value_anchor="You're getting my live R&D"
        )
    ],

    guarantee=Guarantee(
        type="conditional",
        statement="If you complete the Quick Start Flight and don't have your first "
                  "automation running, I'll personally hop on a call and set it up with you.",
        terms="Complete the Quick Start Flight within 7 days"
    ),

    scarcity=Scarcity(
        type="weekly_cap",
        limit="10 new members per week",
        reason="Because I personally review Discord and want to maintain quality"
    ),

    urgency=Urgency(
        type="opportunity_shrinking",
        statement="AI fluency gap compounds. 3 months of learning now = years of advantage. "
                  "The window for early adoption is closing."
    )
)


# ============================================================
# JOURNEYS (each one references THE SAME offer)
# ============================================================

journey_1 = JourneyCore(
    journey_name="Understanding MCP Architecture",
    domain="PAIAB",

    status_quo="I was drowning in context every conversation. Copy-pasting the same "
               "explanations, watching my AI sessions reset to zero.",

    obstacle="I identified the problem when I realized I was spending more time "
             "re-explaining my system than actually building.",

    overcome="I finally understood that MCP servers aren't tools - they're persistent "
             "memory surfaces. I wrapped my patterns into a TreeShell MCP.",

    accomplishment="Now my sessions start with context loaded. 20 minutes of setup → zero. "
                   "It feels like having a colleague who paid attention.",

    the_boon="Your AI doesn't need a bigger context window. It needs external memory "
             "that persists across sessions.",

    demo_description="Screen recording: New Claude session with TreeShell MCP - "
                     "context auto-loads, zero setup, immediate work",

    why_this_matters="This isn't about saving setup time. It's about building AI "
                     "workflows that compound.",

    universal_application="You could do this for YOUR domain. Your patterns, your tools.",

    # Cross-links (filled as published)
    blog_url="https://example.com/blog/mcp-architecture",
    youtube_url="https://youtube.com/watch?v=mcp123",
    github_url="https://github.com/example/treeshell",

    hashtags=["AI", "MCP", "ClaudeAI", "Automation"]
)


# ============================================================
# RENDER EVERYTHING
# ============================================================

print("=" * 60)
print("THE OFFER (used in all CTAs)")
print("=" * 60)
print(SANCTUARY_OFFER.render_short_pitch())

print("\n" + "=" * 60)
print("OFFER ONE-LINER")
print("=" * 60)
print(SANCTUARY_OFFER.render_one_liner())

print("\n" + "=" * 60)
print("JOURNEY CONTENT SUITE")
print("=" * 60)
suite = ContentSuite.from_core(journey_1)
print(suite.discord.render())

print("\n" + "=" * 60)
print("FULL OFFER PITCH (for sales pages)")
print("=" * 60)
print(SANCTUARY_OFFER.render_pitch()[:1500] + "...")
