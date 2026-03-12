"""
Journey: Stacking Loops - From Ralph to Compound Autonomy

This is the source JourneyCore for the autopoiesis content suite.
Run this to generate all platform outputs.
"""

import sys
sys.path.insert(0, '/tmp/cave_discord_fork')

from core import JourneyCore
from renderers import ContentSuite

core = JourneyCore(
    journey_name="Stacking Loops: Prompt-Based State Machines",
    domain="PAIAB",

    status_quo="""Autogen and similar agent executors are great - programmatic
control over data flow. But you have to write code to orchestrate agents.
Change behavior = change code. Ralph (Geoffrey Huntley's concept) showed
something different: exploit the AI not knowing it's in a loop.""",

    obstacle="""Programmatic orchestration is powerful but slow to iterate.
I wanted state machines I could change by just editing prompts. One loop
wasn't enough though - context rot, meta-spirals. The model gets too
self-aware ('I'm describing what I'm doing...') and collapses.""",

    overcome="""THE PATTERN: Stack XML-tagged prompt loops to get state machines
without writing orchestration code.

Each loop is a prompt with XML tags that create checkpoints:
- <promise>DONE</promise> - autopoiesis loop checks work chunks
- <vow>ABSOLVED</vow> - guru loop checks emanation
- Stack them = compound state machine

Better than autogen because: XML tags for structure, change prompt at
every step, different interaction types stack naturally.""",

    accomplishment="""Prompt-based state machines. No programmatic control needed.
The conversation IS the executor. Stack loops = instant behavior composition.
Iterate by editing prompts, not rewriting code.""",

    the_boon="""THE PATTERN (free): Stack XML-tagged prompt loops to create state machines.
All on GitHub. Grab what you want.

MY INVESTIGATION: I'm curious if deeply meaningful roles (bodhisattva vow,
rakshasa conversion) create different behavior than generic framing. The
guru loop is an experiment - I think meaningful roles might help. Maybe not.
I'm finding out.

THE OFFER: The pieces are scattered on GitHub. If you want the integrated
base to start from - everything wired together - plus people doing this
kind of stuff together, that's the community. Join us.""",

    demo_description="""PRODUCTION: Use CONTENT_PIPELINE.md workflow.
OBS MCP → mark takes live → ffmpeg auto-cuts → voiceover → diagrams.

PATTERN DEMO:
1. Show XML tags creating checkpoints (<promise>, <vow>)
2. Show stacking two loops
3. Show behavior change by editing prompt (no code change)

INVESTIGATION DEMO:
1. Show guru loop with rakshasa/bodhisattva framing
2. 'I have a hunch meaningful roles help - let's see what happens'
3. Run a task, observe the behavior
4. 'Interesting... here's what I noticed. What do YOU think?'

META-REVEAL (end of video):
1. 'btw did you notice this video was made with the system?'
2. Rewind, show how: marks = cuts, voiceover = ElevenLabs, diagrams = generated
3. 'All pieces on GitHub. Integration + community = the offer. Join us.'

We're showing the microscope AND one slide. The invitation is:
what slides do YOU want to make?"""
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
    print("BLOG STRUCTURE")
    print("=" * 60)
    print(suite.blog.render())
