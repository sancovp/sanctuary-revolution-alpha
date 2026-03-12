"""
Journey: Meta Video - AI Explains Flights While Following a Flight

The recursive proof: this content is being made BY the system it's ABOUT.
"""

import sys
sys.path.insert(0, '/tmp/cave_discord_fork')

from core import JourneyCore
from renderers import ContentSuite

core = JourneyCore(
    journey_name="Flight Configs: Replayable AI Workflows",
    domain="PAIAB",

    status_quo="""I kept solving the same problems over and over. Each new conversation,
the AI starts fresh. I'd explain the same context, make the same decisions,
hit the same pitfalls. The knowledge was evaporating between sessions.""",

    obstacle="""Context loss is the silent killer of AI productivity. You can't
hand an AI a task and walk away because it doesn't remember HOW you solved
similar problems before. Every session is groundhog day. And I'm too embarrassed
to make content about it manually.""",

    overcome="""I built flight configs - step-by-step prompt templates that encode
HOW to do things. When I start a flight, I get waypoint-by-waypoint guidance
that survives context boundaries. The AI follows the flight, not its own tangents.

And here's the twist: I'm making THIS video by following a content creation flight.
The system is explaining itself BY USING itself.""",

    accomplishment="""No more context rot. No more re-explaining. Flight configs
encode expertise into replayable workflows. And now the AI makes content FOR me
about the system - recursive proof that it works.""",

    the_boon="""FLIGHT CONFIGS = Replayable prompt workflows.
- Encode decisions once, replay forever
- Waypoints survive context boundaries
- AI follows YOUR process, not random tangents

The pattern is open source. This video was made using a content-creation flight.
The proof is the pudding - you're watching it.""",

    demo_description="""RECURSIVE META-DEMO:
1. Show THIS flight config being followed (content_creation_flight)
2. Show the waypoints: Draft JourneyCore → Create Placeholders → Record → Render
3. Reveal: 'You just watched a flight being followed. This video IS the demo.'

TECHNICAL DEMO:
1. fly(path="/project") - browse available flights
2. start_waypoint_journey(config="...") - begin following
3. Show waypoint progression in real-time
4. Show how flight config changes behavior (edit prompt, not code)""",

    why_this_matters="""This is bigger than workflows. It's about compound intelligence.
Every flight config you create makes the NEXT task easier. The system gets smarter
because YOUR decisions persist. Not the AI's knowledge - YOUR expertise.""",

    universal_application="""You could do this for ANY repeatable process:
- Code review flights
- Research flights
- Writing flights
- Debugging flights

If you do something more than once, it should be a flight config.""",

    hashtags=["AI", "Automation", "AgentWorkflows", "PAIA", "CompoundIntelligence"]
)


if __name__ == "__main__":
    suite = ContentSuite.from_core(core)

    print("=" * 60)
    print("DISCORD POST")
    print("=" * 60)
    print(suite.discord.render())

    print("\n" + "=" * 60)
    print("TWITTER THREAD")
    print("=" * 60)
    print(suite.twitter.render())

    print("\n" + "=" * 60)
    print("LINKEDIN POST")
    print("=" * 60)
    print(suite.linkedin.render())

    print("\n" + "=" * 60)
    print("YOUTUBE DESCRIPTION")
    print("=" * 60)
    print(suite.youtube_desc.render())

    print("\n" + "=" * 60)
    print("BLOG STRUCTURE")
    print("=" * 60)
    print(suite.blog.render())
