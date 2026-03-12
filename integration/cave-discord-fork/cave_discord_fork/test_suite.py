"""Test the full ContentSuite - one journey, all platforms."""

from templates import JourneyPost, JourneyBlog, LinkedInPost, TwitterPostSet, ContentSuite

# Same journey, all formats
journey_name = "Understanding MCP Architecture"

discord = JourneyPost(
    journey_name=journey_name,
    status_quo="I was drowning in context every conversation. Copy-pasting the same explanations, watching my AI sessions reset to zero every time.",
    obstacle="I identified the problem when I realized I was spending more time re-explaining my system to Claude than actually building.",
    overcome="I finally understood that MCP servers aren't just 'tools' - they're persistent memory surfaces. I tried wrapping my patterns into a TreeShell MCP.",
    accomplishment="Now my sessions start with context already loaded. I went from 20 minutes of setup per conversation to zero. It feels like having a colleague who actually paid attention.",
    flights_link="[PAIAB/mcp-architecture-flights]"
)

linkedin = LinkedInPost(
    hook="I used to think the AI context window was my enemy. Now I know it was never the problem.",
    story_brief="For months I rebuilt context every AI session. Same explanations, same setup, same frustration. Then I discovered MCP servers aren't just tools - they're persistent memory surfaces. Everything changed.",
    insight="The real insight: your AI doesn't need a bigger context window. It needs external memory that persists across sessions.",
    application="If you're copy-pasting the same context into ChatGPT or Claude every day, you're solving the wrong problem. Build a small MCP for your most-repeated patterns. Watch the friction disappear.",
    cta="What context do you rebuild every session? Curious what patterns people are repeating.",
    hashtags=["AI", "Productivity", "MCP", "ClaudeAI", "Automation"]
)

twitter = TwitterPostSet(
    hook_tweet="My AI used to forget everything between sessions.\n\nNow it remembers my entire system.\n\nThe trick isn't a bigger context window. It's this:",
    media_description="GIF: Starting a new Claude session with TreeShell MCP - shows context auto-loading, zero setup, immediate work",
    reply_context="MCP servers = persistent memory for AI. Your tools, patterns, and context survive session resets.",
    reply_link="https://example.com/mcp-architecture-blog",
    reply_cta="Full breakdown of how I built this"
)

# For blog, using the same data from test_blog.py (abbreviated here)
blog = JourneyBlog(
    journey_name=journey_name,
    hook_attention="What if your AI could remember everything?",
    hook_interest="I spent six months rebuilding context. Then everything changed.",
    hook_desire="You'll understand how to make AI sessions compound.",
    hook_action="Let me show you.",
    topic_attention="This is about MCP - Model Context Protocol.",
    topic_interest="Most people think MCPs are just 'tools.' They're wrong.",
    topic_desire="You'll build AI systems that remember and grow.",
    topic_action="But first, how I got here.",
    personal_attention="Three months ago I was copy-pasting every day.",
    personal_interest="I'd built a compound intelligence system that reset every conversation.",
    personal_desire="What I learned will save you months.",
    personal_action="Here's what works.",
    main_attention="MCPs aren't tools. They're persistent memory surfaces.",
    main_interest="They run as separate processes. They don't reset. They remember.",
    main_desire="You can build workflows that compound. Each session builds on the last.",
    main_action="Let me show you.",
    demo_attention="Watch what happens when I start a session with TreeShell connected.",
    demo_interest="It already knows everything. Zero setup.",
    demo_desire="You could do this for YOUR domain.",
    demo_action="Try building one small MCP.",
    discuss_attention="What context do YOU rebuild every session?",
    discuss_interest="Everyone has that repeated setup.",
    discuss_desire="Sharing helps everyone.",
    discuss_action="Drop it in the comments.",
    cta_attention="If this helped, the like button matters.",
    cta_interest="It shows this to others drowning in context tax.",
    cta_desire="The AI fluency gap is real. Don't fall behind.",
    cta_action="Like. Subscribe. See you next time."
)

# Full suite
suite = ContentSuite(
    journey_name=journey_name,
    discord_post=discord,
    blog_post=blog,
    linkedin_post=linkedin,
    twitter_set=twitter
)

# Print individual formats
print("=== LINKEDIN ===\n")
print(linkedin.render())

print("\n\n=== TWITTER ===\n")
print(twitter.render())
