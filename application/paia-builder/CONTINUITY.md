# PAIA Builder Continuity Notes

## DONE: GEAR Fundamentals Fix (v0.9.0)

### Priority 1: Experience = The Work ✅ COMPLETE

**Implementation:**
- Added `ExperienceEvent` model with event_type, timestamp, component info, GEAR contexts
- Added `ExperienceEventType` enum: COMPONENT_ADDED, TIER_ADVANCED, GOLDEN_ADVANCED, etc.
- Added `experience_events: List[ExperienceEvent]` to GEAR model
- Added `log_experience()` function in gear_ops.py
- All `add_*()` methods now log COMPONENT_ADDED events
- `advance_tier()` logs TIER_ADVANCED events
- `goldify()` logs GOLDEN_ADVANCED events
- `sync_gear()` derives E score from experience_events (base + recency + variety)
- `save_paia()` now calls `sync_gear()` to derive all scores

### Priority 2: GEAR is Fractal ✅ COMPLETE

**Implementation:**
- GEAR docstring documents the fractal nature
- Each ExperienceEvent has fractal contexts: gear_context, achievement_context, reality_context
- sync_gear() implements: E produces G (can't have G without E)
- G = components (OUTPUT of experience)
- E = experience_events timeline (SOURCE)
- A = tier progression (validated through experience)
- R = still self-reported (external validation)

**Semantics are contextual** - each event captures the GEAR dimensions from its perspective.

---

## Onion Architecture Refactor COMPLETE

**Both packages refactored:**
- youknow-kernel ✅ https://github.com/sancovp/youknow-kernel
- paia-builder ✅ https://github.com/sancovp/paia-builder

**Architecture:**
- models.py - Pydantic models ONLY
- util_deps/ - Decomposed atomic modules
- utils.py - Re-exports from util_deps
- core.py - THIN FACADE

**Archi lock ON:** `~/.claude/.codenose_arch_lock`

---

## Current State: v0.8.0 (COMPLETE)

### Architecture Refactor (v0.8.0):
- **REMOVED** `MiniGame` enum and `transition_minigame()` from paia-builder
- Mini-games now live in `sanctuary-revolution` (the game orchestrator)
- paia-builder IS the PAIAB mini-game, not the container of all mini-games

**New Package Structure:**
```
sanctuary-revolution (game orchestrator) @ /tmp/sanctuary-revolution
├── paia-builder (PAIAB - build AI agent) @ /tmp/paia-builder
├── cave-builder (CAVE - business system) @ /tmp/cave-builder [STUB]
└── sanctum-builder (SANCTUM - life architecture) @ /tmp/sanctum-builder [STUB]
```

### System Prompt Validation (v0.7.3):
- `validate_system_prompt(prompt_file_path, config_name)`:
  - Reads file, checks for required `<tag>` and `</tag>` per config
  - Checks bracket matching: `()`, `[]`, `{}`
  - Returns `{"valid": True}` or `{"valid": False, "errors": [...]}`

### PAIA Forking (v0.7.2):
- `PAIAForkType`: child, sibling
- `PAIA` model now has: `forked_from_paia`, `fork_type` fields
- `fork_paia(source_name, new_name, fork_type?, description?, git_dir?, init_giint?)`:
  - Validates source exists against `list_paias()`
  - Copies all 16 component types via `model_copy()`
  - Child forks inherit GEAR state, sibling forks get fresh GEAR
  - Optionally initializes project structure + GIINT

### Agent Forking (v0.7.1):
- `AgentForkType`: child, sibling
- `AgentSpec` now has: forked_from, fork_type fields
- `fork_agent(source_name, new_name, fork_type?, description?)` - creates fork without new GIINT component
- Forks inherit tier and golden status from parent

### Phase 4 Complete:
- `render_system_prompt(prompt_name)` - renders prompt to XML-tagged markdown
- `_generate_claude_md(paia)` - builds full CLAUDE.md from main system prompt
- `check_win()` - now finalizes docs when PAIA is constructed (writes CLAUDE.md)

---

## Previous State: v0.6.4

### 16 Component Types:
1. skills, mcps, hooks, commands, agents, personas, plugins, flights (original 8)
2. metastacks, giint_blueprints, operadic_flows, frontend_integrations, automations (5)
3. agent_gans, agent_duos, system_prompts (3)

### System Prompt Architecture (v0.6.4):
SystemPrompts are section-based with configs for validation:
- **SystemPromptType**: main, persona_frame, subagent
- **SystemPromptSectionType**: background, meta_persona, definitions, rules, architecture, workflows, reinforcement, paia, warnings, custom
- **SystemPromptSection**: section_type + tag_name + content + order
- **SystemPromptConfig**: name + prompt_type + required_sections + optional_sections
- **SystemPromptSpec**: prompt_type + sections[] + config_name + domain + path
- **AgentSpec**: prompt (raw) OR system_prompt_ref (name of SystemPromptSpec)

### Methods:
- `add_system_prompt(name, desc, prompt_type, config_name?, domain?, path?)`
- `add_system_prompt_config(name, prompt_type, required_sections, optional_sections?)`
- `add_section_to_prompt(prompt_name, section_type, tag_name, content, order?)`

### NEXT SESSION TODO:
- Phase 4: `check_win()` finalization and `_generate_claude_md()`
- Consider: validate_system_prompt() against config

---

## Previous State: v0.6.0
- Stateless JSON operation complete
- Version tracking added
- ALL component typing complete (from real sources)
- All components have `custom: Dict[str, Any]` for extension
- Project structure creation works (`new()` with `git_dir`)
- **Phase 2 GIINT integration DONE**
- **Phase 3 Construction Docs DONE**:
  - `_generate_component_doc()` creates markdown for component
  - `_update_construction_docs()` writes component doc + updates gear status
  - `_update_gear_status_doc()` updates 02_gear_status.md overview
  - All add_*(), advance_tier(), goldify() now update docs automatically

## NEXT: PAIA-GIINT Integration Design

### The Mapping (CONFIRMED)
```
GIINT Feature    = Component Type (skills, mcps, hooks, commands, agents, personas, plugins, flights)
GIINT Component  = Individual component (my-skill, my-mcp...)
GIINT Deliverable = Tier level (common, uncommon, rare, epic, legendary)
GIINT Task       = Work to reach that tier (contract as spec)
```

### Flow

#### 1. `new()` creates full project structure
```python
b.new("my-paia", "My AI agent", git_dir="/path/to/repo")
```
Creates:
```
/path/to/repo/
├── .starlog/              # Init STARLOG project
├── construction_docs/
│   ├── 00_overview.md     # Auto-generated summary
│   ├── 01_components/
│   │   ├── skills/
│   │   ├── mcps/
│   │   ├── hooks/
│   │   ├── commands/
│   │   ├── agents/
│   │   ├── personas/
│   │   ├── plugins/
│   │   └── flights/
│   ├── 02_gear_status.md
│   └── 03_changelog.md
├── src/                   # Component code lives here
├── CLAUDE.md              # Builds as PAIA progresses
└── paia.json              # Tracking file (current)
```

Also:
- Registers GIINT project with 8 features (one per component type)
- Links GIINT project to STARLOG path

#### 2. `add_*()` creates GIINT hierarchy
```python
b.add_skill("context-skill", "paiab", "understand", "Context injection")
```
Creates:
- GIINT component "context-skill" under feature "skills"
- 5 deliverables: common, uncommon, rare, epic, legendary
- Tasks for each with TIER_CONTRACTS as specs
- Writes `construction_docs/01_components/skills/context-skill.md`

#### 3. `advance_tier()` completes GIINT tasks
```python
b.advance_tier("skills", "context-skill", "Created with full SKILL.md")
```
- Marks GIINT task for "common" as done
- Updates `construction_docs/01_components/skills/context-skill.md`
- GIINT syncs to GitHub/TreeKanban if configured

#### 4. `check_win()` triggers completion
When True:
- Full repo ready with complete CLAUDE.md
- All construction_docs finalized
- Can swap as active PAIA config

### Implementation Steps

#### Phase 1: Project Structure (this session or next)
- [ ] Add `_init_project_structure()` to core.py
- [ ] Modify `new()` to call it when git_dir provided
- [ ] Create construction_docs/ skeleton
- [ ] Init STARLOG via: `starlog.init_project(path, name, description)`

#### Phase 2: GIINT Integration ✅ DONE
- [x] Add `_init_giint_project()` - creates project with 8 features
- [x] Modify `add_*()` to create GIINT component + deliverables + tasks
- [ ] Add `_update_construction_docs()` helper (deferred to Phase 3)

#### Phase 3: Tier/Golden Updates ✅ DONE
- [x] Modify `advance_tier()` to complete GIINT task (done in Phase 2)
- [x] Modify `advance_tier()` and `goldify()` to update construction_docs
- [x] Add `_update_construction_docs()` helper
- [x] Add `_generate_component_doc()` helper
- [x] Add `_update_gear_status_doc()` helper

#### Phase 4: Completion
- [ ] Modify `check_win()` to finalize docs
- [ ] Add `_generate_claude_md()` for final CLAUDE.md
- [ ] Add swap mechanism for Claude Code config

---

## BEFORE GIINT: Arg Typing Verification

**Decision: Types live in paia-builder, not GIINT.**

Reasoning:
- PAIA-builder is the development interface (everything is either inside base PAIA or new PAIA)
- GIINT is project management (tracks work, not specs)
- paia-builder owns component types and validates them
- When calling down to GIINT, we pass already-validated data

### Typing TODOs

- [x] SkillSpec: ✅ Typed from skill_manager.models.Skill (domain, subdomain, category, what, when, allowed_tools, model)
- [x] MCPSpec: ✅ Typed from CC MCP config (command, args, env, tools, package_path, treeshell)
- [x] PersonaSpec: ✅ Typed from skill_manager.models.Persona (domain, subdomain, frame[required], mcp_set, skillset, carton_identity)
- [x] HookSpec: ✅ HookType enum done
- [x] AgentSpec: ✅ Typed from CC agent config (tools, disallowed_tools, model[enum], permission_mode[enum], skills, prompt)
- [x] FlightSpec: ✅ Typed from starship (domain, category, version, steps, path)

**ALL COMPONENT TYPING COMPLETE - v0.4.0**

**Method:** Ask claude-code-guide for CC primitives, read source for custom libs

### Roadmap

1. **Arg typing** - verify against real sources
2. **GIINT integration** - Phase 2-4
3. **Represent gnosys** - default PAIA representation
4. **Experience system iterations** - the main thing happening in paia-builder
5. **Frontend connection** - user building separately, sends notes down to agent

Two-way interface: Agent updates via code, user updates via frontend, both see same representation.

---

### API References Needed

**STARLOG:**
```python
# From starlog MCP - need to verify exact signatures
starlog.init_project(path: str, name: str, description: str)
starlog.orient(path: str)
```

**GIINT:**
```python
# From llm_intelligence.projects
from llm_intelligence.projects import (
    create_project,
    add_feature_to_project,
    add_component_to_feature,
    add_deliverable_to_component,
    add_task_to_deliverable,
    update_task_status
)
```

---

## What Was Built (v0.3.0)

### Core Features
- **Tier system**: none→common→uncommon→rare→epic→legendary (0-250 pts)
- **Contract fulfillment**: `advance_tier()` requires truthful declaration
- **Goldenization**: quarantine→crystal→golden (with regression)
- **Game phases**: EARLY(L1-5)→MID(L6-9)→LATE(L10-12)→ENDGAME(L13+)→RAID
- **Mini-games**: PAIAB→UNICORN→SANCTUM
- **Version tracking**: `tick_version()` with history
- **Stateless JSON**: All state via JSON files

### Files
- `models.py` - Pydantic models, enums, TIER_CONTRACTS, VersionEntry, HookType
- `core.py` - PAIABuilder class with all methods
- `__init__.py` - Exports

### Typed Enums
- `AchievementTier` - none/common/uncommon/rare/epic/legendary
- `GoldenStatus` - quarantine/crystal/golden
- `GamePhase` - early/mid/late/endgame/raid
- `MiniGame` - paiab/unicorn/sanctum
- `HookType` - PreToolUse/PostToolUse/UserPromptSubmit/Notification/Stop
- `SkillCategory` - understand/preflight/single_turn_process
- `ComponentStatus` - planned/in_progress/complete/validated

### Public API
See previous CONTINUITY.md section - all primitives implemented.

---

## SESSION: 2026-01-11 - SOSEEH Vehicle Thematization

### Key Insight: PAIAB = Building the Vehicle
SOSEEH mapping to PAIAB:
- **Pilot** = Player = OVP = egregore-pilot
- **Vehicle** = PAIA (what you're building)
- **Mission Control** = Dashboards, frontend integrations
- **Interaction Loops** = Chains firing from PAIA chat state

### Work Done This Session
1. **Deleted explain()** - was anti-PIO. YOUKNOW should handle ontology queries.
2. **Thematized status()** - Now shows [PILOT], [VEHICLE], [MISSION CONTROL], [LOOPS]
3. **Thematized select/which** - Vehicle/Pilot language
4. **Thematized new()** - "Hull ready for subsystems"
5. **Added [HIEL] prefixes** - to error messages

### Framework Understanding Gained
- SEAM_REPAIR and REACH cannot be programmed - they're human meta-cognitive processes
- 23 frameworks total: 6 core, 10 primary, 4 secondary, 3 tertiary (see FRAMEWORK_MAP.md)
- Thematization = embedding framework language in ALL strings, not a glossary
- When PAIA reads itself, it gets primed by the vocabulary

### REMAINING: Complete Thematization
- [x] core.py - DONE (all strings thematized)
- [x] utils.py - DONE (update_gear_status_doc thematized)
- [x] util_deps/project.py - DONE (init_project_structure, generate_claude_md)
- [x] util_deps/paia_ops.py - DONE (publish_paia, fork_agent error)
- [x] models.py - DONE (ComponentBase, PAIA, Player, GEAR.display() docstrings)

**THEMATIZATION COMPLETE v0.9.2**

### Key Strings Pattern
```python
# Errors: [HIEL] + problem + seam reference
return f"[HIEL] Vehicle '{name}' not found. Check seam."

# Success: [VEHICLE] or [TOWERING] + action + state
return f"[VEHICLE] {name} initialized. Hull ready for subsystems."
return f"[TOWERING] Subsystem upgraded. Layer complete."

# Status: All four SOSEEH dimensions
[PILOT] OVP/OVA state
[VEHICLE] construction %
[MISSION CONTROL] dashboard status
[LOOPS] chain status
```

### Previous Session Work (preserved)
- paia-builder v0.9.1 with GEAR experience tracking
- sanctuary-revolution v0.4.0 as game orchestrator
- sanctuary-system v0.1.0 with myth layer (WisdomMaverickState, SanctuaryDegree)
- All repos private @ github.com/sancovp/

### Framework Source
Framework docs at: `/home/GOD/tmp/brainhook_session_1/`
- FRAMEWORK_MAP.md - master map of all 23 frameworks
- SOSEEH.md, THERMAL_DYNAMICS.md, HALO.md
- SEAM_REPAIR.md, REACH.md (human processes, not programmable)
