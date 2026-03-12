# RAG Tool/Skill Discovery

**Idea**: Auto-surface relevant tools and skills based on conversation context via hooks.

## The Problem
- 200+ tools across MCPs - hard to remember which exists
- Skills require manual equip/search
- Context switching = forgetting capabilities exist

## The Solution
Hook-based RAG injection that queries existing indexes on UserPromptSubmit.

## Existing Pieces (ALREADY BUILT)
1. **skillmanager.search_skills(query)** - RAG search for skills
2. **gnosys_kit.search_mcp_catalog(query)** - RAG search for tools
3. **gnosys_kit.search_documentation(server, query)** - RAG for tool docs
4. **CartON** - Already does RAG injection via hooks

## What Needs to Be Built
A single hook (`rag_discovery_hook.py`) that:
1. Fires on UserPromptSubmit
2. Extracts key terms from user message (or full transcript summary)
3. Queries `search_skills` + `search_mcp_catalog`
4. Injects top matches as `<system-reminder>` predictions

## Alias Clusters (Enhancement)
Map natural language to capability clusters:
```python
ALIASES = {
    "voice_tts": ["TTS", "voice", "speak", "say", "hear", "audio", "voiceover"],
    "content_pipeline": ["content", "video", "publish", "post", "blog", "youtube"],
    "navigation": ["flight", "waypoint", "starlog", "course", "mission"],
}
```

## Architecture
```
User message
     ↓
UserPromptSubmit hook fires
     ↓
Extract query from message
     ↓
search_skills(query) + search_mcp_catalog(query)
     ↓
Format top 3-5 matches
     ↓
Return as <system-reminder> injection
     ↓
Claude sees: "btw you have X tool that does Y"
```

## TTS Config (from last session)
- Voice: Samantha
- Rate: 202
- Endpoint: POST /speak with {"text": "...", "voice": "Samantha", "rate": 202}

## Related Files
- Skillmanager: /home/GOD/skillmanager-treeshell/
- Strata: /home/GOD/gnosys_strata/
- CartON hooks: ~/.claude/hooks/carton_*.py
