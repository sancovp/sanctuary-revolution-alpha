# Next Session: Events → GEAR

## Primary Task
Investigate the events system in sanctuary-revolution and wire it to GEAR updates.

## Files to Read First
```
/tmp/sanctuary-revolution/sanctuary_revolution/harness/events/  (psyche, system, world)
/tmp/sanctuary-revolution/sanctuary_revolution/harness/core/event_router.py
/tmp/sanctuary-revolution/ARCHITECTURE_HANDOFF.md (section 4)
```

## Context
- Events system EXISTS in harness
- Need to understand: when X event fires → GEAR state should update
- Scoring integration also pending (scoring_persistence.py + reward_system.py)

## Completed This Session
1. ✅ Ralph loop - connected to ralph-orchestrator at /tmp/ralph-orchestrator
2. ✅ Guru pause/resume - added to autopoiesis MCP
3. ✅ Found sanctuary-revolution is the main project (not bare /tmp files)

## Ralph-Orchestrator Note
- Located at /tmp/ralph-orchestrator
- Built TODAY - uses Claude SDK properly
- `pip install /tmp/ralph-orchestrator` then `ralph -a claude --prompt-file X`
- Wrapper at /tmp/autopoiesis_mcp/scripts/isolated-ralph-loop.sh
