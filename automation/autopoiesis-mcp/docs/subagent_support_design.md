# Subagent Support Design

This document captures the design for making autopoiesis work with Claude Code subagents.

**Status:** Design only - not implemented

---

## The Problem

Subagents run independently. Multiple can run in parallel. Each needs its own promise file so they don't conflict. But:

1. SubagentStop hook doesn't include an agent ID
2. The subagent doesn't know its own ID
3. The MCP tool doesn't know which subagent is calling it

## The Solution

Use agent names (human-provided) instead of system IDs, with a registry to track transcript→name mapping.

### Components Needed

1. **Modified MCP tool** - `be_autopoietic("promise", agent_name="research_agent")`
2. **PostToolUse hook on be_autopoietic** - When promise mode, grab agent_name and transcript_path, write to registry
3. **SubagentStop hook** - Look up agent_name from transcript_path, check for that agent's promise file
4. **Registry file** - Maps transcripts to agent names and tracks promise counts

### Flow

```
1. Main agent spawns Task: "You are research_agent. Use that name when calling be_autopoietic."

2. Subagent calls be_autopoietic("promise", agent_name="research_agent")

3. PostToolUse fires:
   - Gets transcript_path from hook input
   - Gets agent_name from tool parameters
   - Writes to /tmp/autopoiesis_registry.json:
     {
       "transcripts": {
         "/path/to/abc123.jsonl": "research_agent"
       },
       "agents": {
         "research_agent": 1  // count of active promises
       }
     }

4. MCP writes /tmp/active_promise_research_agent_1.md

5. Subagent works...

6. SubagentStop fires:
   - Gets transcript_path from hook input
   - Looks up agent_name from registry
   - Checks for /tmp/active_promise_research_agent_1.md
   - Checks for block report or <promise>DONE</promise>
   - Blocks or approves accordingly

7. On completion/block:
   - Decrement count in registry
   - Archive promise file
```

### The `_n` Counter

Same agent name can have multiple concurrent promises (e.g., research_agent runs twice in parallel). The counter handles this:

- First research_agent promise → `_research_agent_1.md`
- Second research_agent promise → `_research_agent_2.md`
- First one completes → count stays at 2, but `_1.md` is archived
- Counter only resets when all promises for that agent are done

### Files

- `/tmp/autopoiesis_registry.json` - The registry
- `/tmp/active_promise_{agent_name}_{n}.md` - Promise files per agent
- `/tmp/block_report_{agent_name}_{n}.json` - Block reports per agent

### Hooks Needed

| Hook | Event | Purpose |
|------|-------|---------|
| `autopoiesis_subagent_stop_hook.py` | SubagentStop | Check promise/block for specific agent |
| `autopoiesis_task_pretool_hook.py` | PreToolUse (Task) | Inject "use be_autopoietic" instruction |
| `autopoiesis_be_autopoietic_posttool_hook.py` | PostToolUse (be_autopoietic) | Register transcript→agent mapping |

### Open Questions

1. What if subagent doesn't provide agent_name? Default to transcript UUID?
2. How to clean up stale registry entries?
3. Should we inject agent_name automatically in PreToolUse instead of requiring main agent to specify?

---

## Why Not Implement Now

This is complex orchestration. The main agent autopoiesis works. Subagent support is a future enhancement if there's demand.
