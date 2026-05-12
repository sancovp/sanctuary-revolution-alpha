# Session 20 Continuity - Agent Harness MVP + KEY REALIZATION

## THE KEY REALIZATIONS

### 1. Claude IS the assembler now.

### 2. CLOSED ON SINGLE AGENT - BIG INSIGHT

**Decision:** Single temporally persistent LLM wrapped by harness. No multi-agent complexity.

**Why this matters:**
- Subagents are dummies (fresh context, disposable)
- Full Claude Code instance = temporally persistent LLM (CLAUDE.md + hooks + omnisanc + self-guru)
- We COULD do multi-agent (multiple full instances coordinated by harness)
- But we DON'T NEED IT YET - it'll be obvious when we do

**What this means for MVP:**
- ❌ No message storage needed
- ❌ No agent coordination layer
- ❌ No multi-agent complexity
- ✅ Harness stays thin (spawn, capture, stream)
- ✅ PocketFlow for simple chaining if needed
- ✅ One full-blown agent with all persistence/hooks/context

**The architecture:**
```
Harness (thin wrapper)
    └── spawns ONE Claude Code instance
            └── with CLAUDE.md + hooks + omnisanc + self-guru
            └── = temporally persistent LLM
            └── Claude IS the agent, not a framework
```

**When to revisit:** When it becomes OBVIOUS we need another full agent in the same world. Not before.

### 3. THE GOD STACK

```
Claude Code
    + prompt injection (Heaven) → chain prompts
    + self-compact → manage context
    + context gauge visibility → know when to compact
    = temporally persistent LLM that manages itself
```

**That's it.** No complex framework. Single agent that:
- Sees its own context %
- Compacts when needed
- Chains prompts via Heaven injection
- IS the assembler

This is god mode.

---

Back then: Claude couldn't code well → needed frameworks/generators (Heaven)
Now: Claude can zero-shot MCPs, skills, hooks → Claude IS the generator

**The architecture:**
```
paia-builder     = SPEC/TRACKING (what are we building?)
Claude (me)      = ASSEMBLER (generates actual code)
gnosys-strata    = MCP INFRASTRUCTURE (runs MCPs)
skillmanager     = SKILL INFRASTRUCTURE (manages skills)
harness          = RUNTIME (wraps Claude Code, spawns specialized instances)
```

**The harness IS Heaven rebuilt on Claude Code + tmux instead of LangChain.**

Pattern:
- Harness spawns Claude Code with specific persona
- Persona configures what "version" of Claude (mcp-builder, skill-maker, etc.)
- Claude generates the component code
- paia-builder tracks the spec/progress
- Infrastructure (gnosys-strata, skillmanager) runs the result

Same as Heaven's LangChain agents with specialized tools, just using Claude Code directly.

---

## What We Built This Session

### game_wrapper/harness MVP WORKING:
- `/tmp/sanctuary-system/game_wrapper/core/harness.py` - tmux control, AGENT_COMMAND env var
- `/tmp/sanctuary-system/game_wrapper/server/http_server.py` - FastAPI + SSE
- **SSE streaming verified working** - events flow through inject → callback → queue → SSE

### Key Features:
- `send_keys(sequence: list)` - sends key sequences with interleaved sleeps
- `capture_pane()` - reads terminal output
- `AGENT_COMMAND` env var required (user provides their own agent command)
- Event routing: inject() → _emit_event() → SSE stream

## Architecture Discovery

### paia-builder = REPRESENTATION ONLY
- Tracks what you declare ("I have MCP called X at tier Y")
- Does NOT generate code, assemble, or know paths
- It's a quest log / achievement tracker
- Agent already knows how to build things - paia-builder just tracks progress

### What We Need = TYPED ASSEMBLERS
- Objects that actually generate code
- Know where libraries are
- Can assemble components
- Heaven might have this...

### Heaven Framework Structure:
```
/home/GOD/heaven-framework-repo/heaven_base/
├── mcps/toolbox_server.py  # FastMCP server exposing registry tools
├── tools/                   # Actual tool implementations
├── registry/                # Registry system
├── baseheaventool.py       # Tool base class
├── make_heaven_tool_from_docstring.py  # Generator?
└── ...
```

## Heaven Patterns to Reuse

**UnifiedChat** (`heaven_base/unified_chat.py`):
- LangChain provider abstraction (Anthropic, OpenAI, Google, Groq, DeepSeek)
- Our `ClaudeCodeChatModel` implements `BaseChatModel` - could add as `ProviderEnum.CLAUDE_CODE`
- This would let Heaven agents use Claude Code via harness!

**Hermes** (`langgraph/hermes_legos.py`, `tool_utils/hermes_utils.py`):
- Template output control + routing to flows
- Controls how LLM outputs structured content

**LangGraph** (`langgraph/foundation.py`):
- Flow orchestration (unfinished but good pattern)

**Acolyte** (`acolyte_v2/`):
- Meta-agent that GENERATES HermesConfigs
- Takes user request → outputs template config
- The "config generator" pattern - agent that creates agent configs

**HermesConfig** (`configs/hermes_config.py`):
- Template-based task configuration
- `args_template` with `{placeholders}`, `variable_inputs`
- Routes to registered agents (strings like "coder_agent")

**LangGraph Legos** (`langgraph/hermes_legos.py`):
- `HermesState` - single agent workflow state
- `ChainState` - multi-agent chain state
- Reusable nodes: `completion_node`, `hermes_node`

**Block Report** - already using in harness output_watcher

**Onion Morph** - super orchestrator pattern (need to find)

## Next Steps

1. **Wire ClaudeCodeChatModel into UnifiedChat** - Heaven agents can use Claude Code
2. **Explore Hermes** for template control - look at make_heaven_tool_from_docstring.py, tools/, registry/
2. **Find if Heaven has typed MCP/component classes** that actually assemble
3. **Integrate harness with typed system** - not paia-builder (representation) but actual assemblers
4. **Package for container** - TWI image with harness + assemblers

## Key Files to Read Next Session:
- `/home/GOD/heaven-framework-repo/heaven_base/make_heaven_tool_from_docstring.py`
- `/home/GOD/heaven-framework-repo/heaven_base/tools/`
- `/home/GOD/heaven-framework-repo/heaven_base/registry/`

## Running State:
- HTTP server may still be running on :8765 (kill with `pkill -f uvicorn`)
- tmux sessions: paia-test, paia-agent may exist
