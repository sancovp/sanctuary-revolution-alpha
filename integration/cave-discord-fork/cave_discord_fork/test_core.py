"""Test the unified JourneyCore → all platforms flow."""

from core import JourneyCore
from renderers import ContentSuite

# ONE source of truth
journey = JourneyCore(
    journey_name="Understanding MCP Architecture",
    domain="PAIAB",

    # Core content
    status_quo="I was drowning in context every conversation. Copy-pasting the same explanations, watching my AI sessions reset to zero every time.",
    obstacle="I identified the problem when I realized I was spending more time re-explaining my system to Claude than actually building. The context window was a sieve.",
    overcome="I finally understood that MCP servers aren't just 'tools' - they're persistent memory surfaces. I tried wrapping my patterns into a TreeShell MCP and suddenly everything clicked.",
    accomplishment="Now my sessions start with context already loaded. I went from 20 minutes of setup per conversation to zero. It feels like having a colleague who actually paid attention to the last six months.",

    # The boon
    the_boon="Your AI doesn't need a bigger context window. It needs external memory that persists across sessions. MCPs are that memory.",

    # Demo
    demo_description="Screen recording: Starting new Claude session with TreeShell MCP connected - shows context auto-loading, available tools appearing, zero setup, immediate productive work",

    # Expansion
    why_this_matters="This isn't just about saving setup time. It's about building AI workflows that compound. Each session builds on the last instead of starting from scratch.",
    universal_application="You could do this for YOUR domain. Your patterns, your tools, your context. The MCP holds the memory so your conversations can focus on actual work.",

    # Cross-links (fill these as you publish)
    blog_url="https://example.com/blog/mcp-architecture",
    youtube_url="https://youtube.com/watch?v=xxx",
    github_url="https://github.com/example/treeshell-mcp",
    patreon_url="https://patreon.com/example",
    flights_path="PAIAB/mcp-architecture-flights",
    website_url="https://example.com",

    # Metadata
    hashtags=["AI", "MCP", "ClaudeAI", "Automation", "Productivity"]
)

# Generate ALL content from ONE source
suite = ContentSuite.from_core(journey)

print("=" * 60)
print("DISCORD POST")
print("=" * 60)
print(suite.discord.render())

print("\n" + "=" * 60)
print("TWITTER SET")
print("=" * 60)
print(suite.twitter.render())

print("\n" + "=" * 60)
print("YOUTUBE DESCRIPTION")
print("=" * 60)
print(suite.youtube_desc.render())

print("\n" + "=" * 60)
print("BLOG (first 800 chars)")
print("=" * 60)
print(suite.blog.render()[:800])
