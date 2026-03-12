"""Test the JourneyPost template with a real example."""

from templates import JourneyPost, DomainOverview

# A real journey - learning MCP architecture
journey = JourneyPost(
    journey_name="Understanding MCP Architecture",

    status_quo="I was drowning in context every conversation. Copy-pasting the same "
               "explanations, losing track of what tools existed, watching my AI "
               "sessions reset to zero every time.",

    obstacle="I identified the problem when I realized I was spending more time "
             "re-explaining my system to Claude than actually building. The context "
             "window was a sieve.",

    overcome="I finally understood that MCP servers aren't just 'tools' - they're "
             "persistent memory surfaces. I tried wrapping my most-used patterns "
             "into a single TreeShell MCP and suddenly the AI remembered everything.",

    accomplishment="Now my sessions start with context already loaded. I went from "
                   "20 minutes of setup per conversation to zero. My AI knows what "
                   "I'm working on, what tools exist, what patterns I use. It feels "
                   "like having a colleague who actually paid attention to the last "
                   "six months.",

    flights_link="[PAIAB/mcp-architecture-flights]"
)

print(journey.render())
print("\n" + "="*60 + "\n")

# Domain overview
overview = DomainOverview(
    domain_name="PAIAB",
    domain_essence="PAIAB is where we build AI that builds AI. Personal AI Agent "
                   "Infrastructure and Bootstrap. The tools that make the tools.",
    what_lives_here="Journeys about MCP development, agent architecture, compound "
                    "intelligence, context engineering, and the meta-game of making "
                    "AI systems that improve themselves."
)

print(overview.render())
