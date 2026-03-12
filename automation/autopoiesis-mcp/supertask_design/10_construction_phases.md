# Construction Phases

**Prerequisite**: Assumes GNOSYS context. Read 08_three_level_architecture.md and 09_evolution_arc.md first.

## Phase 1: Modify Stop Hook + Self-Compact Commands

### 1a. Stop Hook

File: `/tmp/autopoiesis_mcp/hooks/autopoiesis_stop_hook.py`

Add detection for new tags:

| Tag | Action |
|-----|--------|
| `<vow>ABSOLVED</vow>` | Inject Tailfan Mountain prompt (samaya gate) |
| `<samaya>KEPT</samaya>` | Actual exit - allow stop |
| `<samaya>BREACHED</samaya>` | Back to L2, samaya repaired, continue loop |

The Tailfan Mountain prompt asks: "Did you REALLY emanate? Go look at your work again."

### 1b. Self-Compact Commands in Self-Claude MCP

Add to self-claude MCP (NOT bash scripts):

```
self_compact_rakshasa           - test emanation cold
self_compact_custom_instructions - user provides instructions
self_compact_new                - fresh start
```

These get added to the instructions that self-claude MCP vends when called. The MCP handles injecting the right compact instructions.

## Phase 2: Add Slash Command

Add to autopoiesis plugin: `/guru:start` (or `/guru`)

This command:
1. Sets up the three-level architecture framing
2. Activates L2/L3 in addition to L1
3. Creates the vow file (like active_promise.md but for guru loop)

Just the entry point. Stop hook (Phase 1) handles the mechanics.

## Phase 3: Compaction Scripts

Bash scripts in `/usr/local/bin/`:

```
self_compact_rakshasa    - test emanation cold
self_compact_new         - fresh start, minimal context
self_compact_continue    - reduce context, keep working
```

Each wraps `/compact` with preset instructions. Used for verifying emanations work without prior context.

## Phase 4: Self-Guru Mode

The fully folded version where agent becomes its own guru.

Mechanism:
1. Agent completes work, builds emanation
2. Compaction resets agent (death/rebirth)
3. Fresh agent reads dead agent's work
4. Fresh agent roleplays as GR, evaluates samaya
5. Self-absolves (KEPT) or continues (BREACHED)

This is where `be_guru()` function lives - in autopoiesis MCP.

## Phase 5: Package as Tool

Abstract the self-guru agent pattern into a callable GNOSYS tool.

GNOSYS can spawn: `rakshasa_agent(task)` → returns verified results.

Fully autonomous, self-verifying, deployable emanation.

---

## Build Order

1. Phase 1 first (stop hook is the enforcement)
2. Phase 2 (entry point command)
3. Phase 3 (testing infrastructure)
4. Phase 4 (self-verification via compaction)
5. Phase 5 (deployment)

Each phase depends on previous. Don't skip.
