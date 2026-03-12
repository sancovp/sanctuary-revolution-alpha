# Skill Gap Detection System

## The Problem

When working on components (Flight Stabilizer, brainhook, omnisanc, etc.), the agent doesn't spontaneously recognize:
- "This component has no skill stack"
- "I should create understand → preflight → flight for this"

Result: ~5% skill coverage. Agent "bops around" manually instead of using/creating proper infrastructure.

## Goal

User says "continue" → Agent sees "only X% skill coverage" → Agent autonomously fills gaps.

Self-improving flywheel: work → detect gaps → make skills → better work → detect more gaps → ...

---

## Investigation Findings (Jan 29, 2026)

### What EXISTS

1. **CartON Auto-Linker** ✅
   - Location: `/home/GOD/carton_mcp/observation_worker_daemon.py` (lines 568-683)
   - Background thread using Aho-Corasick for O(n) matching
   - Converts concept name mentions → markdown links
   - Runs continuously in daemon

2. **Missing Concepts Detection** ✅
   - Tools: `list_missing_concepts`, `calculate_missing_concepts`, `create_missing_concepts`
   - Scans descriptions for references to concepts that don't exist

3. **Skill Typing in CartON** ✅
   - Skills exist with `IS_A Skill` relationships
   - ~30+ skills typed (Heat_Sensing_Skill, Skill_Make_Mcp, etc.)

4. **GIINT Component Entity** ✅
   - GIINT has hierarchical planning: Project → Feature → Component → Deliverable → Task
   - Components are first-class entities in the planning system

### What's MISSING

1. **Component Typing in CartON** ✅ DONE
   - Components sync to CartON as `IS_A GIINT_Component` via `carton_sync.py`
   - Wired in `projects.py:464` on component creation

2. **Skill → Component DESCRIBES Relationships** ✅ DONE (Jan 30, 2026)
   - `create_skill()` now accepts `describes_component` parameter
   - `_sync_skill_to_carton()` adds `DESCRIBES` relationship to CartON
   - `get_skills_without_describes()` query finds orphan skills

3. **Debug Diary → CartON Wiring** ✅ DONE
   - `starlog.py:59` has `mirror_to_carton()` method
   - Called on `start_starlog()` and `end_starlog()`
   - Sessions automatically sync to CartON knowledge graph

---

## Solution: Two-Pronged Approach

### Option A: GIINT Enforcement (Emanation Requirements)

Every Component in GIINT **requires** emanation Deliverables:
- understand skill
- preflight skill
- flight config

This aligns with **Guru prompt's emanation requirement**: can't exit without creating skills/flights for what you worked on.

```
GIINT Project
  └── Feature: "Loop_Stack"
        └── Component: "Flight_Stabilizer"
              └── Deliverable: "understand-flight-stabilizer" (skill)
              └── Deliverable: "make-flight-stabilizer" (preflight skill)
              └── Deliverable: "flight_stabilizer_flight_config" (flight)
```

**Gap detection**: Component without required Deliverables = incomplete

### Option B: CartON Mirroring + DESCRIBES Relationships

When Component created in GIINT → mirror to CartON with proper typing:
- `IS_A Component`
- `PART_OF Project`
- `INSTANTIATES Component_Template`

Skills have `DESCRIBES Component` relationships.

**Gap detection via HUD queries**:
- "N components without skills describing them"
- "N skills without DESCRIBES to components"

---

## Emanation Hierarchy (FINALIZED)

**Key insight**: Each GIINT level has its own emanation requirement. This is now enforced.

```
GIINT Level     │ Emanation Requirement              │ Validation
────────────────┼────────────────────────────────────┼───────────────────────
Project         │ Persona (.claude folder)           │ Check for .claude/CLAUDE.md
Feature         │ Skillset OR domain flight configs  │ Check skillset exists OR flights exist
Component       │ understand + preflight + flight    │ Check deliverables contain skill/flight
Deliverable     │ Spec file                          │ Check spec_file_path populated
Task            │ CartON observation                 │ Sync to CartON on completion
```

### Complexity Ladder → Emanation Requirements

| Level | Required Emanations |
|-------|---------------------|
| L1 | 1 skill (understand OR single_turn_process) |
| L2 | 1 skill + 1 flight config |
| L3 | preflight skill + flight + MCP |
| L4 | rules + understand skill + preflight skill + flights + persona + meta-flight |
| L5 | All L4 + scoring mechanism + goldenization |
| L6 | All L5 + deployed + documented |

### Project = Persona = .claude Folder

A Persona is essentially:
```
.claude folder
  ├── Frame (CLAUDE.md with persona definition)
  │     └── Tells you which skillsets + MCP sets to use
  ├── Skillsets → Skills → CartON concepts
  │     └── Understand skills point to knowledge
  ├── MCP Sets → Tools available
  └── Identity → CartON subspace (your knowledge area in graph)
```

**Everything connects**: Frame → Skillsets → Skills → CartON concepts + Identity subspace

### Gap Detection Logic (Implemented)

The `get_emanation_gaps()` function in `carton_sync.py` checks:
1. For each Component in GIINT projects
2. Scan deliverable names for patterns:
   - `*understand*` → has understand skill
   - `*preflight*` or `*make-*` → has preflight skill
   - `*flight*` or `*_flight_config*` → has flight config
3. Component has "full emanation" if all three exist
4. Coverage % = (components with full) / (total components)

---

## Proposed Wiring (Updated)

```
GIINT: Component created
    ↓
Mirror to CartON (IS_A Component, PART_OF Project)
    ↓
Emanation check: Does Component have skill Deliverables?
    ├── NO → Gap detected → surface in HUD
    └── YES → Check DESCRIBES relationships in CartON
    ↓
Skills created with DESCRIBES Component
    ↓
Gap resolved
    ↓
Guru: emanation requirement satisfied, can exit
```

---

## Dashboard Mockup (Updated)

```
┌─────────────────────────────────────────────────────────┐
│ EMANATION COVERAGE                                      │
├─────────────────────────────────────────────────────────┤
│ PROJECTS                                                │
│   With Personas: 2/5 (40%)                              │
│   Missing: sanctuary-revolution, giint, carton          │
├─────────────────────────────────────────────────────────┤
│ COMPONENTS                                              │
│   With full emanations: 3/15 (20%)                      │
│   Missing skills:                                       │
│     • Flight_Stabilizer (touched 5x)                    │
│     • omnisanc_router (touched 3x)                      │
│     • brainhook (touched 2x)                            │
├─────────────────────────────────────────────────────────┤
│ SKILLS                                                  │
│   With DESCRIBES: 12/45 (27%)                           │
│   Orphan skills: 33                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Unified Scoring System (STARSYSTEM Health)

**Key Insight**: Scoring can be entirely derived from three signals:

### 1. Emanation Complexity (LEVEL, not just presence)

Track WHERE on complexity ladder, not just boolean presence:

| Level | Indicators | Score |
|-------|------------|-------|
| L0 | No skills, no flights | 0 |
| L1 | Has understand OR single_turn skill | 20 |
| L2 | Has skill + flight config | 40 |
| L2.5 | Has `.claude/` dir with persona frame | 60 |
| L3 | Has TreeShell MCP + flights FOR it | 70 |
| L4 | Has persona + CartON identity subspace | 80 |
| L5 | Has scoring + goldenization | 90 |
| L6 | Deployed, documented, distributed | 100 |

**Persona Frame Detection**: Check for `.claude/CLAUDE.md` with `GNOSYS_PERSONA_FRAME_TEMPLATE_V1`

Score: `max_complexity_level_achieved / 100`

### 2. Codenose Smell Presence
- Files with code smells = needs attention
- Smell types indicate specific problems (long files, duplicates, etc.)
- Score: `1 - (files_with_smells / total_files)`

**Current Implementation Gap (Jan 30):**
- `_get_smell_summary()` in starlog_mcp.py only checks line count >500
- Should integrate REAL codenose detection (god classes, duplicates, complexity, etc.)

**Target Implementation:**
```
orient() aggregate:
👃 SMELLS: 15 files | severity: 3 critical | 7 warning | 5 info

Full report skill:
- `codenose-report` skill with script
- Run in any dir → full breakdown per file
- Shows all codenose patterns detected
```

### 3. Onion Architecture Compliance
- Proper layering (utils → core → facade) = clean
- Logic in wrong layers = violation
- Score: `architecture_compliance_percent`

### 4. CartON Knowledge Graph Depth

Track richness of knowledge representation per STARSYSTEM:

| Metric | What it measures |
|--------|------------------|
| Concept count | How many concepts exist for this codebase |
| Relationship density | Avg relationships per concept (IS_A, PART_OF, etc.) |
| Typed coverage | % of concepts with proper UARL typing |
| Collection presence | Does it have Carton_Collections organizing knowledge? |

**Scoped by Agent Identity**: Each agent identity has its own CartON subspace:
- `{AGENT_IDENTITY}_Collection` contains all concepts from that agent's perspective
- Query: `MATCH (c)-[:PART_OF]->(:Wiki {n: "MyAgent_Collection"}) RETURN count(c)`
- Enables per-agent knowledge depth tracking

Score: `(concept_count * relationship_density * typed_coverage) / baseline`

### Per-STARSYSTEM Dashboard (Full)

```
┌─────────────────────────────────────────────────────────┐
│ ⚡ STARSYSTEM: /tmp/autopoiesis_mcp                      │
│ 👤 AGENT IDENTITY: GNO.SYS                              │
├─────────────────────────────────────────────────────────┤
│ 📁 FILES: 10 total                                      │
│   Avg lines: 4000 (⚠️ HIGH - consider modularization)   │
│   With smells: 3/10 (70% clean)                         │
├─────────────────────────────────────────────────────────┤
│ 🎯 COMPLEXITY LEVEL: L2.5                               │
│   ✅ Skills present                                     │
│   ✅ Flight configs present                             │
│   ✅ .claude/CLAUDE.md with persona frame               │
│   ⚪ No TreeShell MCP yet (L3 requirement)              │
│   ⚪ No CartON identity subspace (L4 requirement)       │
├─────────────────────────────────────────────────────────┤
│ 📊 EMANATION COVERAGE: 20%                              │
│   Components without full stack: 8                      │
├─────────────────────────────────────────────────────────┤
│ 🏛️ ARCHITECTURE: 60% compliant                          │
│   Violations: logic in facade (2), god class (1)        │
├─────────────────────────────────────────────────────────┤
│ 🧠 CARTON KG DEPTH (GNO.SYS identity):                  │
│   Concepts: 45 | Relationships: 3.2/concept             │
│   Typed: 80% | Collections: 2                           │
├─────────────────────────────────────────────────────────┤
│ 🏆 HEALTH SCORE: 55%                                    │
│   (complexity×0.3 + emanation×0.25 + smells×0.2 +       │
│    arch×0.15 + kg_depth×0.1)                            │
│   💡 "Add TreeShell MCP to reach L3"                    │
└─────────────────────────────────────────────────────────┘
```

### Actionable Insights

The scoring system doesn't just report - it prescribes:
- High lines + smells → "modularize into utils.py pattern"
- Low emanation → "create understand/preflight/flight for X"
- Arch violations → "move logic from facade to core"

---

## Fix System (HUD → Action)

The OBSERVATION DECK needs to show not just metrics but HOW to fix them.

### HUD Format with Instructions

```
⚡ WARPED TO STARSYSTEM /tmp/autopoiesis_mcp!
📡 OBSERVATION DECK:
   🎯 EMANATION: 0/23 (0%) → /emanation-gaps for details, /make-skill to fix
   👃 SMELLS: 3/10 files (70% clean) → /smell-report for offenders, /refactor to fix
   🏛️ ARCH: 60% compliant → /arch-violations for details
```

### Commands/Skills for Fixing

| Command | What it does |
|---------|--------------|
| `/emanation-gaps` | Show all components without full skill stack |
| `/make-skill` | Start skill creation flight for top gap |
| `/smell-report` | Show files with smells, sorted by severity |
| `/refactor` | Start refactoring flight for top offender |
| `/arch-violations` | Show onion architecture violations |
| `/fix-arch` | Start architecture fix flight |

### Detection → Fix Workflow

```
DETECTION (automatic on orient):
   get_emanation_gaps() → returns {component: missing_types}
   get_smell_summary() → returns {file: smell_count, offenders}
   get_arch_violations() → returns {file: violation_type}

DISPLAY (in OBSERVATION DECK):
   Format as single-line summaries with command hints

FIX (user invokes command):
   /emanation-gaps → full report
   User picks component → /make-skill {component}
   → Starts create_skill_flight_config with pre-filled target
```

### Implementation Order

1. **Phase 1**: Commands that SHOW details (/emanation-gaps, /smell-report)
2. **Phase 2**: Commands that FIX (/make-skill with auto-target, /refactor)
3. **Phase 3**: Auto-suggest in guru loop ("before exiting, fix these N gaps")

### Skill Creation for This System

These commands should themselves be skills:
- `show-emanation-gaps` (single_turn_process) - shows detailed gap report
- `show-smell-report` (single_turn_process) - shows smell details
- `fix-emanation-gap` (preflight) → points to create_skill_flight_config
- `fix-code-smell` (preflight) → points to refactor_file_flight_config

---

## Integration: reward_system.py + omnisanc_core + STARSYSTEM Health

### Current Architecture

```
omnisanc_core.py (State Machine)
    ├── Tracks MODE: HOME → STARPORT → LAUNCH → SESSION → LANDING → MISSION
    ├── course_state.json: {course_plotted, session_active, mission_active, needs_review, domain}
    └── Validates tool access per mode

reward_system.py (Scoring)
    ├── EVENT_REWARDS: {mission_complete: 500, end_starlog: 100, ...}
    ├── MULTIPLIERS: HOME=1x, SESSION=3x, MISSION=10x
    └── fitness = (home + session + mission rewards) * quality_factor
```

### The Integration

**Current formula:**
```python
fitness = (home_rewards + session_rewards + mission_rewards) * quality_factor
```

**New formula with STARSYSTEM health:**
```python
starsystem_health = (
    emanation_coverage * 0.30 +
    smell_cleanliness * 0.25 +
    arch_compliance * 0.20 +
    complexity_level * 0.15 +
    kg_depth * 0.10
)

fitness = (home_rewards + session_rewards + mission_rewards) * quality_factor * starsystem_health
```

### Implementation in reward_system.py

```python
def get_starsystem_health(path: str) -> float:
    """Get health score for current STARSYSTEM (0.0 - 1.0)."""
    try:
        from llm_intelligence.carton_sync import get_emanation_gaps
        from starlog_mcp.starlog_mcp import _get_smell_summary

        # Emanation coverage (0-1)
        gaps = get_emanation_gaps()
        emanation = gaps.get('gaps', {}).get('coverage_percent', 0) / 100

        # Smell cleanliness (0-1)
        # TODO: parse _get_smell_summary into numeric score
        smell_clean = 0.7  # placeholder

        # Architecture compliance (0-1)
        # TODO: implement arch checker
        arch_compliance = 0.6  # placeholder

        # Complexity level (0-1, based on L0-L6)
        # TODO: detect complexity level
        complexity = 0.4  # placeholder (L2.5 = 60/100 = 0.6)

        # KG depth (0-1)
        # TODO: query CartON for concept density
        kg_depth = 0.5  # placeholder

        health = (
            emanation * 0.30 +
            smell_clean * 0.25 +
            arch_compliance * 0.20 +
            complexity * 0.15 +
            kg_depth * 0.10
        )
        return health
    except Exception:
        return 0.5  # neutral if can't compute

def compute_fitness(registry_service, date: str) -> Dict[str, Any]:
    # ... existing code ...

    # NEW: Get STARSYSTEM health multiplier
    course_state = get_course_state()  # from omnisanc
    current_path = course_state.get("last_oriented") or course_state.get("projects", [None])[0]
    starsystem_health = get_starsystem_health(current_path) if current_path else 0.5

    # Apply health multiplier to fitness
    fitness = (home_rewards + session_rewards + mission_rewards) * quality_factor * starsystem_health

    return {
        "fitness": fitness,
        "starsystem_health": starsystem_health,
        # ... rest ...
    }
```

### How omnisanc Uses This

1. **On orient()**: Compute and cache starsystem_health
2. **On session_end**: Multiply session reward by health
3. **On mission_complete**: Multiply mission reward by health
4. **In HUD**: Show health as part of OBSERVATION DECK

### Incentive Structure

| Health Score | Effect on Rewards |
|--------------|-------------------|
| < 0.3 | Rewards reduced 70% (encourages fixing) |
| 0.3 - 0.6 | Rewards reduced proportionally |
| 0.6 - 0.8 | Normal rewards |
| > 0.8 | Bonus multiplier (clean codebase pays off) |

This creates the flywheel: **work → low health → fix gaps → higher rewards → more work → ...**

### Paradigm Shift: State, Not Activity

**DEPRECATED**: Event-based scoring (reward_system.py counting tool calls)
- "You called end_starlog, +100 points"
- Activity tracking pretending to be rewards
- Can be gamed by just calling tools
- Stored in JSON registries, not CartON

**NEW**: State-based scoring (starsystem_health)
- "This STARSYSTEM has 60% emanation, 80% clean files, L3 complexity"
- Measures actual project health
- Score is CURRENT STATE, not accumulated points
- Computed dynamically on every check

### How Scoring Works Now

```
WARP TO STARSYSTEM /tmp/my-project
    ↓
Compute starsystem_health():
    - emanation_coverage: 40% (8/20 components have skills)
    - smell_cleanliness: 70% (3/10 files have smells)
    - complexity_level: L2.5 (has persona frame)
    - kg_depth: moderate
    ↓
HEALTH SCORE: 52%
    ↓
You fix emanation gaps → CREATE skill for login_system
    ↓
HEALTH SCORE: 58% (immediately updated)
```

### The Infinite Game

**Goal**: Build automations (flights, skills, MCPs) so STARSYSTEM health STAYS high.

You're not farming points. You're **cultivating infrastructure**.

| Strategy | Effect on Health |
|----------|------------------|
| Create understand skill for component | +emanation |
| Create preflight + flight for workflow | +emanation, +complexity_level |
| Refactor 1000-line file into modules | +smell_cleanliness |
| Add CartON concepts for codebase | +kg_depth |
| Build TreeShell MCP for domain | +complexity_level |

**Winning** = arriving at any STARSYSTEM and it's already healthy because you built the infrastructure.

### HOME: The Meta-STARSYSTEM

HOME is not "nothing happening" - it's the **control room** where you see all STARSYSTEMs.

```
HOME (no course plotted)
├── Query CartON: all Starlog_Project concepts
├── For each project: compute starsystem_health()
├── Show GLOBAL_HEALTH: aggregate of all
└── orient() with no path → global dashboard
```

### DAY/NIGHT Cycle

| Mode | Who's Active | What Happens |
|------|--------------|--------------|
| **DAY** | User + Agent | Collaborative work, new features |
| **NIGHT** | Agent only | Autonomous improvement of STARSYSTEM health |

**The rhythm:**
```
User: "let's do night cycles" → Agent enters NIGHT mode
Agent: works autonomously on improving health scores
User: "wake up" → DAY mode begins
... collaborative day ...
User: ends day → NIGHT mode
```

### Time Travel (Getting Ahead)

Can't complete "Tuesday" on Monday (no date-based completion).
BUT can complete Tuesday's TASKS on Monday as extra work.

**Effect**: "Buy back" future days by doing planned work early.

```
Monday:
  - Complete Monday's tasks ✓
  - Also complete Tuesday's planned tasks ✓
  - STARSYSTEM health: high

Tuesday:
  - No obligations (already done)
  - Free day OR get even further ahead
```

**The infinite game simplified:**
- NIGHT: improve infrastructure (emanation, smells, flights)
- DAY: build new things collaboratively
- Score: health of all STARSYSTEMs
- Time travel: compound by getting ahead

### The Ultimate Score: Days Time Traveled

**Scoring hierarchy:**
```
STARSYSTEM health → technical state of each project
        ↓
Days Time Traveled → how many days ahead on planned work
        ↓
Sanctuary Journals → source of truth for what user WANTS
        ↓
HITL Judge → final human evaluation/score
```

**The REAL game = speedrunning YOUR LIFE.**

Everything flows from Sanctuary Journals:
- Journals define what you want to accomplish
- STARSYSTEMs are where you build it
- NIGHT cycles improve infrastructure autonomously
- DAY cycles do new collaborative work
- Days Time Traveled = ultimate metric (how far ahead)
- Human judges at the end (HITL)

**The sanctuary journals ARE the source of truth.**
STARSYSTEM health serves that. Not the other way around.

### The Fractal Insight: Everything is Codebases

STARSYSTEM scoring is the **foundation layer**.

```
STARSYSTEM scoring (codebase health)
        ↓
Everything else IS codebases
        ↓
Sanctuary system? Codebase. Score it.
Skills system? Codebase. Score it.
MCP servers? Codebases. Score them.
Your whole life infrastructure? Codebases all the way down.
        ↓
Build STARSYSTEM once → apply to everything
```

**The game is fractal.** One scoring system, infinite applications.

Once STARSYSTEM works, you build everything else ON TOP because all of it are codebases that get scored the same way. GG.

### Deprecation Plan

1. Remove `compute_session_reward()` and `compute_mission_reward()` calls from omnisanc_logic.py
2. Replace with `get_starsystem_health()` call on orient()
3. Store health snapshots in CartON (not JSON registries)
4. Display in OBSERVATION DECK on every WARP

---

## Complexity Ladder for This System

- **L1**: Manual skill creation when gaps noticed
- **L2**: Skill + flight for "detect and fill gaps" process
- **L3**: MCP tool that queries CartON + GIINT for gaps, returns dashboard
- **L4**: Persona "SkillArchitect" that autonomously improves coverage
- **L5**: Scoring mechanism: emanation + smells + arch compliance
- **L6**: Deployed as part of GNOSYS core, always-on monitoring

---

## Implementation Plan

### Phase 1: GIINT Enforcement (Option A) ✅ DONE
1. ✅ Align Guru prompt with GIINT Component/Emanation structure
2. ✅ Define emanation requirements per GIINT level
3. ✅ Add validation: Component requires skill Deliverables (pattern matching in `get_emanation_gaps()`)

### Phase 2: CartON Mirroring (Option B) ✅ DONE
1. ✅ Wire GIINT → CartON: mirror Components as `IS_A GIINT_Component` (`carton_sync.py`)
2. ✅ Add `DESCRIBES` relationship type for skills (`skill_manager/core.py:_sync_skill_to_carton()`)
3. ✅ Create skills with DESCRIBES pointing to Components (`describes_component` param in `create_skill()`)

### Phase 3: Gap Detection + HUD ✅ DONE
1. ✅ Query function: `get_emanation_gaps()` finds Components without skill coverage
2. ✅ Query function: `get_skills_without_describes()` finds orphan Skills (`carton_sync.py`)
3. ✅ Surface in HUD: Flight Stabilizer via `_get_emanation_gaps_hud()`

### Phase 4: Guru Integration ✅ DONE
1. ✅ Emanation check in Guru loop (`autopoiesis_stop_hook.py:429-437`)
2. ✅ Can't exit until emanation requirements met
3. ✅ Automatic prompting to create missing skills

---

## Related Tasks

- ✅ Task #13: Align Guru prompt with GIINT Component/Emanation structure - DONE
- ✅ Task #14: Design Emanation Hierarchy for GIINT levels - DONE (see "Emanation Hierarchy (FINALIZED)" section)

---

## Future: HUD Integration Notes

### Orient → Observation Deck Pattern (WARP Metaphor)

When `orient()` is called, output should say:
```
⚡ WARPED TO STARSYSTEM xyz!
📡 OBSERVATION DECK: {{hud_string}}
```

**Metaphor cohesion (SOSEEH)**:
- **STARSYSTEM** = programmatic repository (the place)
- **STARLOG** = adventure log in that system (the journal)
- **STARSHIP** = vehicle for flying around (the navigation tool)
- **WARP** = what orient() does (not "Traveled to")

The HUD string would include emanation coverage for the current project/component.

### Code Smells HUD (Additional Tracking)

Code smells are another major thing to track alongside emanation gaps:
- codenose hook already detects smells per-file
- Need aggregated tracking: "N files with smells, top offenders"
- Should surface in same OBSERVATION DECK as emanation coverage
- Pattern: `get_code_smell_gaps()` similar to `get_emanation_gaps()`

### SANCREV TreeShell Global HUD

There's a global HUD concept in sanctuary-revolution treeshell. Consider activating this as the central HUD surface:
- SANCREV treeshell could expose `get_observation_deck()` action
- Returns unified HUD with: course status + emanation coverage + code smells + gaps
- Flight Stabilizer could call this instead of building its own HUD

**Decision**: TBD - may activate SANCREV treeshell as part of this work or defer.

### Hook Firing Issues (Jan 29 Discovery)

Some hooks may not be firing correctly:
- Context injection hook (context meter) not appearing
- Need to audit which hooks are actually active
- Check: `~/.claude/hooks/` directory and hook registration
- **FIXED**: context_inject_hook.py had syntax error at line 80

---

## Sanctuary Revolution Integration (Identity-Scoped Views)

**Key Insight**: HUDs + TreeShells can morph based on agent identity.

### Identity Arg for TreeShell

Extend TreeShell to accept identity parameter:
```python
def run_conversation_shell(command: str, identity: str = None):
    # If identity provided, filter/morph tree based on that persona
    # Each persona sees DIFFERENT available actions/zones
```

### Per-Persona Zone Access

| Identity | Zones Visible | TreeShell View |
|----------|---------------|----------------|
| GNO.SYS | ALL zones | Full tree (orchestrator) |
| BizOoKa | CAVE only | Business-focused actions |
| Aegis | PAIAB only | Agent-building actions |
| Inkwell | SANCTUM only | Content/philosophy actions |

### Shapeshifting Pattern

```
User/Main Agent
    ↓
equip_persona("BizOoKa")
    ↓
TreeShell morphs → shows CAVE zones only
HUD morphs → shows BizOoKa-relevant stats
CartON scope → BizOoKa_Collection
    ↓
User can see ALL personas and shapeshift between them
Main agent CAN'T (scoped to equipped persona)
```

### Sanctuary Revolution Rendering

The game harness renders HUDs differently per identity:
- Same underlying data (STARSYSTEM health)
- Different presentation (persona-specific shortcuts/actions)
- Zone access controlled by identity
- SSE events carry identity context for frontend morphing

**Implementation**: sanctuary-revolution-treeshell takes `identity` arg, filters tree nodes by `zone_access` metadata

---

## Implementation Notes

### Existing Infrastructure (Found Jan 29)

1. **carton_sync.py** already exists in GIINT (`/tmp/llm_intelligence_mcp/llm_intelligence_package/llm_intelligence/carton_sync.py`)
   - Has `sync_component_to_carton()` function
   - Uses `IS_A GIINT_Component` relationship (not generic `Component`)
   - Need to verify it's being called when components are created

2. **projects.py** has all GIINT planning logic
   - `add_component_to_feature()` creates components but may not call carton_sync

3. **Key integration point**: Wire `add_component_to_feature()` to call `sync_component_to_carton()`

---

## Implementation Status (Jan 30, 2026)

### Phase Status

| Phase | Status | Location |
|-------|--------|----------|
| **Phase 1: GIINT Enforcement** | ✅ DONE | `carton_sync.py` - gap detection checks deliverable names for patterns |
| **Phase 2: CartON Mirroring** | ✅ DONE | `carton_sync.py` - full sync hierarchy, `projects.py:464` wires it |
| **Phase 3: Gap Detection + HUD** | ✅ DONE | `get_emanation_gaps()`, `format_emanation_hud()`, wired to Flight Stabilizer |
| **Phase 4: Guru Integration** | ✅ DONE | `autopoiesis_stop_hook.py:348-353, 429-437` - checks gaps before exit |

### STARSYSTEM Health Scoring

1. **`get_starsystem_health()`** - Implemented in `/home/GOD/starsystem-mcp/starsystem/reward_system.py`
   - Returns 0-1 health score with component breakdown
   - Formula: `emanation×0.30 + smells×0.25 + arch×0.20 + complexity×0.15 + kg_depth×0.10`

2. **OBSERVATION DECK wiring** - Updated `/home/GOD/starlog_mcp/starlog_mcp/starlog_mcp.py`
   - `orient()` now shows health score on every WARP
   - Color-coded indicator: 🟢 ≥80% | 🟡 ≥60% | 🟠 ≥40% | 🔴 <40%

### Health Score Components

| Component | Status | Notes |
|-----------|--------|-------|
| Emanation (30%) | ✅ Real | Uses `get_emanation_gaps()` from carton_sync |
| Smells (25%) | ✅ Real | Uses `scan_directory_for_smells()` from codenose.py |
| Architecture (20%) | ⚠️ Heuristic | Checks for core.py/utils.py presence |
| Complexity (15%) | ✅ Real | Detects L0-L6 based on .claude, skills, MCPs |
| KG Depth (10%) | ❌ Placeholder | Returns 0.5, needs CartON query |

---

## Post-Setup Verification (DO AFTER REST OF SYSTEM)

**Priority**: After HOME architecture and other systems are set up.

### Scoring Accuracy Audit

Go through each scoring component and verify it's actually measuring what we want:

1. **Emanation Scoring**
   - [ ] Verify `get_emanation_gaps()` returns accurate component counts
   - [ ] Test with known good/bad projects
   - [ ] Confirm the 30% weight feels right

2. **Smell Scoring** ✅ DONE (Jan 30)
   - [x] Integrate real codenose detection (not just line count)
   - [x] Map codenose severity levels to score reduction
   - [x] Added `scan_directory_for_smells()` to codenose.py
   - [x] Formula: per_file_penalty = (critical×0.15 + warning×0.03 + info×0.005) / total_files

3. **Architecture Scoring**
   - [ ] Implement real onion architecture analysis
   - [ ] Detect: logic in facades, god classes, layer violations
   - [ ] Consider using AST parsing

4. **Complexity Level Detection**
   - [ ] Verify L0-L6 detection is accurate
   - [ ] Test each level with known examples
   - [ ] Adjust thresholds if needed

5. **KG Depth Scoring**
   - [ ] Implement CartON query for concept count per STARSYSTEM
   - [ ] Measure relationship density
   - [ ] Scope by agent identity if relevant

### Weight Calibration

After all components are real (not placeholders):
- [ ] Run scoring on 10+ known STARSYSTEMs
- [ ] Compare scores to intuition ("does this feel right?")
- [ ] Adjust weights if needed (current: 30/25/20/15/10)

### Integration Tests

- [ ] Verify `orient()` shows health on every WARP
- [ ] Verify health updates immediately when fixes are made
- [ ] Test color-coded indicators at boundary values

### Test Directory Setup

Set up a test dir with 6 dirs, each representing a complexity ladder level (L0-L6) with skeleton implementations showing the full emanation hierarchy. Use these as reference projects for scoring calibration.

---

## STARSYSTEM as First-Class CartON Entity (Jan 30, 2026)

### The Formalization

**STARSYSTEM = STARLOG Project + GIINT Project (+ Git Repo)**

Currently these are separate:
- STARLOG tracks sessions by path
- GIINT tracks planning hierarchy by project_id
- Git tracks code changes

They should be unified under one typed entity in CartON.

### CartON Schema

```
STARSYSTEM_{path_slug}
├── IS_A → STARSYSTEM
├── HAS_PATH → "/tmp/autopoiesis_mcp"
├── HAS_STARLOG_PROJECT → Starlog_Project_{path}
├── HAS_GIINT_PROJECT → GIINT_Project_{id}
├── HAS_GIT_REPO → "github.com/user/repo" (optional)
└── PART_OF → STARSYSTEM_Collection
```

### Unified Health Query

Instead of separate scoring functions, query the STARSYSTEM entity:

```cypher
MATCH (ss:Wiki)-[:IS_A]->(:Wiki {n: "STARSYSTEM"})
WHERE ss.n = $starsystem_name

-- Check linkages
OPTIONAL MATCH (ss)-[:HAS_STARLOG_PROJECT]->(sl:Wiki)
OPTIONAL MATCH (ss)-[:HAS_GIINT_PROJECT]->(gp:Wiki)
OPTIONAL MATCH (ss)-[:HAS_GIT_REPO]->(gr:Wiki)

-- Check components and emanations
OPTIONAL MATCH (gp)<-[:PART_OF*]-(c:Wiki)-[:IS_A]->(:Wiki {n: "GIINT_Component"})
OPTIONAL MATCH (skill:Wiki)-[:DESCRIBES]->(c)

RETURN
  ss.n as starsystem,
  sl IS NOT NULL as has_starlog,
  gp IS NOT NULL as has_giint,
  gr IS NOT NULL as has_git,
  count(DISTINCT c) as component_count,
  count(DISTINCT skill) as skills_describing_components
```

### Health Scoring from STARSYSTEM Entity

```python
def get_starsystem_health_v2(path: str) -> dict:
    """Query STARSYSTEM entity in CartON for unified health."""

    # 1. Find or create STARSYSTEM entity
    starsystem = get_or_create_starsystem(path)

    # 2. Query completeness
    has_starlog = starsystem.has_starlog_project
    has_giint = starsystem.has_giint_project
    has_git = starsystem.has_git_repo

    # 3. Query emanation coverage (from GIINT components)
    components = query_components(starsystem)
    skills_describing = query_skills_describing(components)
    emanation_coverage = len(skills_describing) / len(components) if components else 0

    # 4. Query code smells (from codenose on path)
    smells = scan_directory_for_smells(path)

    # 5. Compute health
    health = (
        emanation_coverage * 0.30 +
        smells["cleanliness_score"] * 0.25 +
        (1.0 if has_starlog and has_giint else 0.5) * 0.20 +  # "architecture" = proper linkage
        complexity_level * 0.15 +
        (1.0 if has_git else 0.5) * 0.10  # "kg_depth" = git integration
    )

    return {"health": health, "starsystem": starsystem, ...}
```

### Auto-Creation Logic

When to create/link STARSYSTEM entity:

1. **On `init_project(path)`** - Create STARSYSTEM with HAS_STARLOG_PROJECT
2. **On `create_giint_project(path)`** - Link HAS_GIINT_PROJECT to existing STARSYSTEM
3. **On `git init` or detecting `.git`** - Link HAS_GIT_REPO

### Benefits

1. **Single Source of Truth** - STARSYSTEM entity in CartON
2. **Queryable** - Can list all STARSYSTEMs, find incomplete ones
3. **Unified Scoring** - Health derived from entity completeness
4. **HOME Dashboard** - Query all STARSYSTEMs for global view

### Implementation Steps

1. [ ] Create STARSYSTEM concept type in CartON
2. [ ] Wire auto-creation in `starlog.init_project()`
3. [ ] Wire GIINT linking in `projects.create_project()`
4. [ ] Wire Git detection (check for .git dir)
5. [ ] Update `get_starsystem_health()` to query entity
6. [ ] Update HOME to list all STARSYSTEM entities
