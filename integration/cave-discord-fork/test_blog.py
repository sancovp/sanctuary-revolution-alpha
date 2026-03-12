"""Test the JourneyBlog template with a real example."""

from templates import JourneyBlog

blog = JourneyBlog(
    journey_name="Understanding MCP Architecture",

    # HOOK
    hook_attention="What if your AI could remember everything from every conversation you've ever had with it?",
    hook_interest="I spent six months rebuilding context every single session. Then I discovered something that changed everything.",
    hook_desire="By the end of this, you'll understand how to make your AI sessions actually compound instead of resetting to zero.",
    hook_action="Let me show you what I found.",

    # TOPIC INTRO
    topic_attention="This is about MCP - Model Context Protocol - and why it's the most important thing happening in AI tooling right now.",
    topic_interest="Most people think MCPs are just 'tools for Claude.' That's like saying the internet is just 'email.' They're missing the real thing.",
    topic_desire="Once you see what MCPs actually are, you'll be able to build AI systems that remember, learn, and grow with you.",
    topic_action="But first, let me tell you how I got here.",

    # PERSONAL
    personal_attention="Three months ago I was copy-pasting the same explanations into Claude every single day. Same context. Same setup. Same exhaustion.",
    personal_interest="I'd built this whole compound intelligence system - skills, flights, personas - and every conversation started from scratch. The irony was killing me.",
    personal_desire="What I learned trying to solve this problem is going to save you months of the same frustration.",
    personal_action="Here's what actually works.",

    # AD (optional)
    ad_content="*If you want the actual flight configs I use for MCP development, they're available in the PAIAB Patreon. Link in description.*",

    # MAIN CONTENT
    main_attention="Here's the thing: MCPs aren't tools. They're persistent memory surfaces.",
    main_interest="When you wrap your patterns into an MCP server, it runs as a separate process. It doesn't reset when your conversation ends. It remembers. Your tools, your state, your context - it all persists across sessions.",
    main_desire="This means you can build AI workflows that actually compound. Each session builds on the last instead of starting from zero.",
    main_action="Let me show you what this looks like in practice.",

    # DEMO
    demo_attention="Watch what happens when I start a new Claude session with my TreeShell MCP connected.",
    demo_interest="See that? It already knows my project structure, my available tools, my current flight config. Zero setup. I just start working.",
    demo_desire="You could do this for YOUR domain. Your patterns. Your workflows. The MCP holds the memory so your conversations can be about actual work, not setup.",
    demo_action="Try building one small MCP for your most-repeated context. You'll feel the difference immediately.",

    # DISCUSSION
    discuss_attention="Here's what I'm curious about: what context do YOU rebuild every session?",
    discuss_interest="Everyone has that thing they explain over and over. That setup they repeat. That context they paste.",
    discuss_desire="Sharing this helps everyone - we learn from each other's pain points. And I might build MCPs for the common ones.",
    discuss_action="Drop it in the comments. What's YOUR context tax?",

    # ANNOUNCEMENTS
    announce_content="Next week I'm releasing a full walkthrough of building your first MCP from scratch. Subscribe so you don't miss it.",

    # CTA
    cta_attention="If this helped you understand MCPs differently, that like button actually matters.",
    cta_interest="It tells YouTube to show this to other people drowning in context tax. We're building a community of people who get this.",
    cta_desire="The AI fluency gap is real. Three months of learning compounds fast. Don't fall behind.",
    cta_action="Like. Subscribe. Check the Patreon for the flight configs. See you in the next one."
)

print(blog.render())
