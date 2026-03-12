# Context Engineering Patterns

## The Compaction Instruction Pattern

Before compacting, run this check:

> "We still have context left so we should make sure we have thought about everything we SHOULD think about from this context."

This forces the agent to:
1. Review what was discovered/built
2. Identify unresolved questions
3. Capture insights that might be lost
4. Note dependencies and next steps

## Pattern: Pre-Compact Sweep

```
1. What did we build? (artifacts)
2. What did we learn? (insights)
3. What questions remain? (unresolved)
4. What depends on what? (dependencies)
5. What's the next atomic step? (continuation)
```

## Pattern: Compaction Instructions

When compacting, specify what the fresh context needs:
- Key files to read
- State of the system
- Next task to pick up
- Any gotchas or warnings

Example:
```
/compact Read /tmp/autopoiesis_mcp/supertask_design/11_meta_brainhook_architecture.md
and 12_paia_control_plane.md. L2/L3 guru loop works. Next: build meta_brainhook hook.
```

## Pattern: Context Checkpoints

Create "checkpoint" files at key moments:
- After major insight
- Before architectural decision
- When switching contexts

These become the "save points" that fresh contexts can load from.

## Library Vision

Eventually this becomes `context_engineering`:
- `checkpoint(name, content)` - save context state
- `restore(name)` - load checkpoint into fresh context
- `sweep()` - pre-compact analysis
- `compact_with(instructions)` - compact with specific handoff

## This File Itself

This file is a meta-pattern: documenting the patterns we use for context engineering so future sessions can use them too.
