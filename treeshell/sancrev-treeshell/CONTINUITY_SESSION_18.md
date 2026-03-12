# Session 18 CONTINUITY - Sanctuary Revolution Architecture

## What We Accomplished

### Docs Created (17 total in /tmp/sanctuary-revolution-treeshell/docs/)
1. omnisanc_state_machines.md
2. home_mode_map.md
3. heros_journey_mapping.md
4. journey_integration_spec.md
5. narrative_hierarchy.md
6. starlog_improvements.md
7. home_learning_loop.md
8. day_night_cycle.md
9. sanctuary_journaling.md
10. soseeh_paia_mapping.md
11. context_engineering_library.md
12. creation_processes.md
13. groundhogs_day_game.md
14. treeshell_spec.md
15. hooks_and_loops.md
16. omnisanc_queue_spec.md
17. paia_harness_architecture.md **[BREAKTHROUGH]**

---

## Key Architecture Decisions

### PAIA Formula
```
PAIA = Substrate + Loop + Memory + Identity + CartON + [Personas]
     = Claude Code + autopoiesis + STARLOG + persona + CartON identity
```

### The Flow
```
PAIA → MVS → SJ → VEC → (PAIA levels up) → repeat
```

### Omnisanc Architecture
```
Omnisanc Hook (imports MCP manager)
    ↓
Queue (Redis/Celery/n8n webhook)
    ↓
n8n → World (APIs, Discord, payments, etc.)
```

### Hooks Hierarchy
```
Meta Brainhook (failsafe - observe only when all dies)
    ↓
Omnisanc (orchestrator - state machine + MCP manager)
    ↓
Interaction Loops (autopoiesis, guru, ralph, brainhook)
```

### TreeShell as Game Interface
```
sancrev ""              → HUD (shows recent stuff)
sancrev enter X         → Load basin context
sancrev flights         → See available flights
sancrev launch Y        → Start waypoint journey
sancrev complete        → Extract learnings, return home
```

### Groundhog's Day Game
Every conversation starts with smashed context. Must play GDG first:
- Crystal Forest shows all context basins
- Choose which to enter
- Context loaded
- Then proceed to Starport

---

## Treekanban Status

**Two packages exist:**
- `heaven-bml` = GitHub issues backend (gh CLI)
- `heaven-bml-sqlite` = SQLite HTTP client (Electron app API)

**MCP exists in source (not pip):**
- `/home/GOD/tmp/heaven-bml-public/mcp_server/server.py`
- `/home/GOD/tmp/heaven-bml-private/mcp_server/server.py`

**Next:** Package MCP into pip, or add to strata config from source.

**DISCONNECT FOUND:**
- canopy-mcp uses `heaven_base.tools.registry_tool` (NOT SQLite)
- heaven-bml-sqlite uses HTTP to Electron SQLite server
- treekanban frontend uses SQLite server
- **NONE ARE CONNECTED** - need unified storage

---

## 24/7 Operation (Not Yet Implemented)

Needs:
1. Self-compact timing fix
2. Self-restart timing fix
3. Escape key send to interrupt output
4. Meta brainhook failsafe

---

## Next Session Priorities

1. **Treekanban MCP** - wrap heaven-bml-sqlite for agent access (or add heaven-bml MCP to strata)
2. **understand-git-workflows skill** - extract BML patterns, gh CLI tricks, issue workflows into a skill
3. **24/7 fixes** - Escape key, timing
4. **Sancrev TreeShell implementation** - actual code
5. **Context engineering library** - loop executor

---

## Key Insights

- **Personas ≠ Subagents**: Persona = who I'm being (transformation), Subagent = separate agent (delegation)
- **Loops are the differentiator**: Without a loop, it's just Claude Code with prompts
- **Queue is the boundary**: Inside = PAIA territory, Outside = World territory
- **TreeShell embeds calls**: See node → fire → no lookup needed
- **Omnisanc can import MCP manager**: No separate orchestration MCP needed

### BREAKTHROUGH: PAIA Harness Architecture

- **PAIA is NOT Claude Code**: Claude Code is just the hands (substrate)
- **PAIA = Daemon + World State + Event System + Memory + Personality**
- **Harness spawns agents**: Tmux attachment, not tmux run
- **Simulation time**: Events fire, state drifts, time passes even when no agent running
- **RNG/Likelihood modules**: Probabilistic personality injection based on state machines
- **be_myself() loop**: Agent reports state → probabilities adjust → random injections fire
- **Railgun integration**: Frontend injects harness → harness configures everything → spawns agent → zero manual setup
- **This is infrastructure**: A harness for code agent applications, not just "an agent"
- **PSYCHOBLOOD FOUND**: psycho_blood_1.json contains the ontology - 9 universal human states (Ground→Arousal→Reverence→Shame→Fear→Rupture→Integration→Compassion→Decay)
- **Harness = Psychoblood Simulator**: The psyche configs simulate agents moving through these states
- **THREE config types**: Psyche (who I am) + World (what happens to me) + System (what harness is doing)

### CODE WRITTEN: /home/GOD/game_wrapper/
```
core/harness.py              # Main daemon
events/psyche/module.py      # Basic RNG personality
events/world/module.py       # External events
events/system/module.py      # Infrastructure
events/psychoblood/
├── psychoblood.py           # 9-state machine
├── observer_psychics.py     # Meta-awareness (unconscious→lucid)
└── berserking.py            # WANGTANG (authentic presence)
utils/rng/base.py            # RNGEvent + RNGModule
server/http_server.py        # FastAPI for Railgun
```

### CRITICAL PATH FOR NEXT SESSION:
**Replace unified_chat in Heaven with Claude Code harness**
File: `/home/GOD/heaven-framework-repo/heaven_base/unified_chat.py`

### NEXT SESSION TODO:
- Configure tmux for harness control (existing frameworks are hype, just do it)
- Wire PAIA class with subprocess tmux send_keys
- Test control loop
- **HEAVEN INTEGRATION**: Harness enables Heaven → Claude Code → Heaven tool executor loop
  - Heaven UI → HTTP → Harness → tmux → Claude Code → back to Heaven tool executor
  - THE FULL LOOP WORKS NOW
  - **HEAVEN = agent framework that adapts agents into/out of ANY other agent framework**
  - Harness is the adapter layer. Claude Code is just one substrate. PAIA is portable.
  - **IMPOSE ANY AGENT FRAMEWORK ON CLAUDE CODE**: LangChain, CrewAI, AutoGPT, anything
  - Claude Code = execution substrate. Heaven = framework layer on top.

### WANGTANG Formula (from berserking.py):
- Fear → 0, Arousal → 100, Compassion → 100, Logic lattice → 75
- Creates "gravity well" = authentic presence / power field
- Tibetan: wangtang (དབང་ཐང་) = Trungpa's "authentic presence"
- Perception you know what you're doing beyond the task level

---

*Session 18 (2026-01-11/12)*
