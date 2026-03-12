# Architecture Handoff - Sanctuary Revolution

## What Was Done - Session 2026-01-16

### 1. SR v0.5.0 - Harness + Omnisanc Integration

**Harness exports added to SR:**
```python
from sanctuary_revolution import (
    PAIAHarness, HarnessConfig, HookControl, HookType,
    EventRouter, Event, EventSource, EventOutput,
    OutputWatcher, DetectedEvent, EventType,
)
```

**Omnisanc state machine added:**
```python
from sanctuary_revolution import (
    OmnisancPhase,  # HOME → MISSION → STARPORT → SESSION → LANDING → HOME
    LandingStep,    # PENDING → LANDING_ROUTINE → SESSION_REVIEW → GIINT_RESPOND → COMPLETE
    CourseState,    # Full state from /tmp/heaven_data/omnisanc_core/.course_state
    load_course_state, get_phase, is_home, is_in_session, is_landing,
)
```

### 2. Harness ↔ Hooks Connection (ALREADY WIRED)

The connection between harness and Claude Code hooks EXISTS:
- `harness/core/event_router.py` WRITES → `/tmp/paia_hooks/pending_injection.json`
- `~/.claude/hooks/paia_injection_hook.py` READS ← `/tmp/paia_hooks/pending_injection.json`
- `harness/core/hook_control.py` WRITES → `/tmp/hook_config.json`

**Flow:**
```
Harness EventRouter → writes events → /tmp/paia_hooks/
                                           ↓
Claude Code hooks ← reads events ← paia_injection_hook.py
```

### 4. Remaining Work - Agent Completion

**Agent mechanics (before minigame logic):**
1. **n8n integration** - workflow automation, external triggers
2. **Guru loop controls** - autonomous running (tmux-based)
3. **Ralph loop controls** - `claude -p` runs for isolated subagent work
4. **GEAR ↔ Events bidirectional bus** - Events connects GEAR to Frontend (Railgun):
   - Outbound: GEAR changes → emit event → SSE → frontend displays
   - Inbound: User accepts/rejects in UI → event → updates GEAR proof
   - Agent BUILDS components, User provides PROOF via frontend
   - G/E/A/R proofs require user confirmation, Events carries those decisions
5. **Scoring integration** - wire existing scorers into event runtime:
   - `~/.claude/hooks/scoring_persistence.py`
   - `/home/GOD/starsystem-mcp/starsystem/reward_system.py`
   - Totalizing event runtime = scoring is just another event consumer

**Then the sequence:**
```
Agent mechanics (guru/ralph/events/n8n)
       ↓
Minigame event logic (x-builder events)
       ↓
Sancrev integration (GEAR + VECs)
       ↓
GNOSYS compilation
       ↓
Self-hosting loop → pre-launch/alpha
```

### Research Item: Meta-Interpreter Structure

SR has `bootstrap_self_reference()` in SanctuaryOntology - "YOUKNOW containing YOUKNOW". But is this a proper meta-interpreter or just naive nesting?

**Investigate:**
1. Study real meta-interpreter implementations (Lisp eval/apply, Scheme)
2. What's required: reification, reflection, eval/apply loop
3. Compare to what `bootstrap_self_reference()` actually does
4. Is it sufficient or needs proper structure?

**Key insight:** Sancrev = GEAR while building VECs (paias + journeys + products) across paia-builder, cave-builder, sanctum-builder. Progressively more self-hosting and ontologized as it continues.

### 5. Files Changed
- `/tmp/sanctuary-revolution/sanctuary_revolution/__init__.py` - harness + omnisanc exports
- `/tmp/sanctuary-revolution/sanctuary_revolution/omnisanc_state.py` - NEW (CourseState model)
- `/tmp/sanctuary-revolution/pyproject.toml` - v0.5.0, omnisanc in game deps
- `/tmp/sanctuary-system/game_wrapper/__init__.py` - deprecation notice

---

## Previous Session Notes

1. **Moved game_wrapper from sanctuary-system to sanctuary-revolution**
   - FROM: `/tmp/sanctuary-system/game_wrapper/`
   - TO: `/tmp/sanctuary-revolution/sanctuary_revolution/harness/`
   - Created `__init__.py` with exports

2. **Clarified the architecture:**
   ```
   youknow_kernel (validation primitives)
          ↓
   sanctuary-system (models only - SanctuaryEntity, VEC, MVS, etc.)
          ↓
   sanctuary-revolution (game + harness + omnisanc)
          ↓
   sanctuary-revolution-treeshell (MCP interface)
   ```

3. **Confirmed sanctum-builder already imports SS** - mythic layer available there

## Still TODO

1. ~~**Update SR's main `__init__.py`** to export harness~~ ✅ DONE
2. ~~**Wire omnisanc into SR** for state machine tracking~~ ✅ DONE
3. **x-builders import YOUKNOW** for validation on `add_*()` calls
4. ~~**pip install -e** sanctuary-revolution after changes~~ ✅ DONE
5. ~~**Update sanctuary-revolution-treeshell** to use harness~~ ✅ DONE
6. ~~**Remove game_wrapper from sanctuary-system**~~ ✅ DONE (added deprecation notice)

## Key Insight: Mythic Layer Mapping

Builders stay domain-specific. SR maps them mythically:
- paia-builder → PAIA, GEAR (AI-focused)
- sanctum-builder → SanctuaryEntity (life-focused, already imports SS)
- cave-builder → funnels (biz-focused)

SR's `integrate_paiab()` is where PAIA becomes OVP within SANCTUM.

## The Meta-Interpreter Pattern

```
Base:    OnionArchSpec → MCPSpec → PluginSpec → ContainerSpec → DeliverableSpec
Meta:    YOUKNOW validates at builder level
Super:   compile_deliverable() builds validated specs
REPL:    TreeShell exposes unified SR
Homoic:  PAIA builds PAIA, YOUKNOW validates YOUKNOW
```

## Files Changed
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/` - NEW (moved from SS)
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/__init__.py` - exports

## KEY INSIGHT: SR Codes The Entire Phase Space

SR + YOUKNOW types encode the ENTIRE transformation journey:
```
PIOEntity      → what exists (ontology)
Reach          → how things connect (analogical_reach.py)
Bridge         → how to cross (metastack_bridge.py)
ValidationLevel → where you ARE:
  EMBODIES     → OVP (wasteland, promise)
  MANIFESTS    → building
  REIFIES      → OVA (in sanctuary)
  INSTANTIATES → OEVESE (transmuting)
```

The game IS the phase space. YOUKNOW validates position. SR tracks trajectory.
This is homoiconic closure - system describing transformation IS transformation.

## Next Session
1. Finish wiring harness into SR core.py
2. Add omnisanc integration
3. Test `pip install -e /tmp/sanctuary-revolution`
4. Strategize on game logic connections

---

## SESSION: 2026-01-16 - n8n Integration Architecture

### What Was Done

**Server consolidation:**
- `container_handoff.py` marked DEPRECATED → use `http_server.py`
- Added missing endpoints to `http_server.py`:
  - `POST /execute` - run bash/python code
  - `POST /interrupt` - send Esc to Claude
  - `POST /exit` - send /exit to Claude
  - `POST /force_exit` - send C-c
  - `POST /kill_agent_process` - kill claude process
- `orchestrator.py` copied to `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/`

**Architecture clarified:**
```
HOST:
├── orchestrator.py (:8420) - spawns containers, routes messages
├── n8n - workflow automation, external triggers
└── Electron frontend

CONTAINERS (all use same server):
└── http_server.py (:8421) - full featured (SSE, hooks, execute, claude control)
```

**n8n integration pattern:**
```
INBOUND: webhook/schedule → n8n → orchestrator:8420 → container http_server
OUTBOUND: agent calls n8n → external APIs (Stripe, GitHub, Slack, etc.)
```

n8n is the BOUNDARY LAYER - handles world↔system interface. Internal routing is just HTTP.

### Files Changed
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/docker/container_handoff.py` - deprecated
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/http_server.py` - added endpoints
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/orchestrator.py` - NEW

### Still TODO
1. Update orchestrator.py to use http_server port/endpoints (currently expects container_handoff)
2. Create docker-compose with orchestrator + n8n + agent containers
3. Build `paia-agent:latest` Docker image using http_server.py
4. Create n8n workflow templates
5. Test end-to-end: n8n → orchestrator → container → result

---

## SESSION: 2026-01-16 - Chaining Patterns Research

### Heaven-Framework Patterns Reviewed

Explored `/home/GOD/heaven-framework-repo/heaven_base/` for chaining patterns:

**Key files:**
- `configs/hermes_config.py` - HermesConfig (templated execution config) + DovetailModel (chain connector)
- `langgraph/hermes_legos.py` - LangGraph state machines (HermesState, ChainState)
- `tool_utils/hermes_utils.py` - hermes_step, use_hermes_dict, handle_hermes_response

**Useful patterns:**
1. **HermesConfig** - template with `args_template` + `to_command_data(variable_inputs)` for runtime injection
2. **DovetailModel** - `expected_outputs` + `input_map` to connect step outputs→inputs
3. **hermes_step** - execute + handle response (block reports, goal completion)

### paia-builder Already Has Most of This

Checked `/tmp/paia-builder/paia_builder/models.py`:

- `FlightSpec` + `FlightStepSpec` - replayable workflows (agents run these via waypoint, no need to program)
- `AutomationSpec` - n8n workflows
- `AgentGANSpec` / `AgentDUOSpec` - agent chaining with initiators
- `DeliverableSpec` - callable compilation target

### Key Insight: DeliverableSpec

Current `DeliverableSpec` in paia-builder is PAIA-specific:
```
spec_type, spec_name, container, output_image, github_repo, trusted
```

But a GENERAL DeliverableSpec would be any callable compilation target.

**User mentioned:** giint-llm-intelligence may have a better version. Package is installed (`pip show giint-llm-intelligence` shows v0.1.8) but source location unclear. Check for `Deliverable` patterns there.

### Clarified Architecture

**DeliverableSpec needs subtypes:**
```
DeliverableSpec (base - abstract)
├── GIINTProjectDeliverable  → points to giint project file
├── PromptDeliverable        → arbitrary string prompt
└── TemplatedDeliverable     → HermesConfig-style with variable injection
```

**Chaining = List[DeliverableSpec]** - subtype doesn't matter for chaining logic.

**DovetailModel** stays same - maps outputs→inputs between any deliverable types.

**Reuse HermesConfig** for TemplatedDeliverable (already works, don't rebuild).

### Next Steps

1. **Check if giint projects already map to paia-builder specs** - what's the connection?
2. **Add DeliverableSpec subtypes** to paia-builder or SR
3. **Move/copy HermesConfig** from heaven-framework to SR (or import it)
4. **Wire orchestrator.py** to execute any DeliverableSpec subtype
5. Don't program flights - agents run them, waypoint handles state

### GIINT ↔ paia-builder Connection FOUND

**Already wired in `/tmp/paia-builder/paia_builder/util_deps/giint_ops.py`:**
```python
from giint_llm_intelligence.core import (
    create_project, add_feature_to_project, add_component_to_feature,
    add_deliverable_to_component,  # ← Deliverable is HERE
    add_task_to_deliverable, update_task_status
)
```

**GIINT → paia-builder mapping:**
- GIINT Project = PAIA
- GIINT Feature = Component Type (skills, mcps, hooks, etc.)
- GIINT Component = Individual component (my-skill, my-mcp)
- GIINT Deliverable = Tier level (common, uncommon, rare, epic, legendary)
- GIINT Task = Work to reach that tier (contract as spec)

**What this means:**
- Deliverable concept lives in `giint_llm_intelligence.core`
- paia-builder already calls down to it
- Need to find giint-llm-intelligence source to see full Deliverable model
- Then can extend/subtype for chaining (GIINTProjectDeliverable, PromptDeliverable, TemplatedDeliverable)

### BUG: DeliverableSpec NOT using giint Deliverable

**Two separate concepts with same name - NOT connected:**

| paia-builder `DeliverableSpec` | giint `Deliverable` |
|-------------------------------|---------------------|
| "Callable compilation target" | Tier level (common→legendary) |
| Builds PAIA images | Tracks component progress |
| `spec_type`, `spec_name`, `container` | Part of task hierarchy |
| Standalone Pydantic model | Used by `add_deliverable_to_component()` |

**This is wrong.** DeliverableSpec should USE giint's Deliverable system.

### Fix Required

1. Find giint-llm-intelligence source
2. Look at giint's Deliverable model
3. Make paia-builder's DeliverableSpec either:
   - Extend/wrap giint Deliverable, OR
   - Be replaced by giint Deliverable + subtypes
4. Then wire orchestrator to execute them
5. Then add chaining (DovetailModel pattern)

---

## SESSION: 2026-01-16 - GIINT Interactive Builder Wiring

### What Was Done

**Rewrote `/tmp/paia-builder/paia_builder/util_deps/giint_ops.py`:**
- Removed auto-generation garbage (create_giint_component with 5 tier deliverables)
- Added proper interactive building functions:
  - `add_component()` - creates component only, NO auto-deliverables
  - `add_deliverable()` - adds deliverable + initial task
  - `add_task()` - adds task to deliverable
  - `complete_task()` - marks task done
  - `attach_spec_to_component()` - saves spec JSON and attaches to giint

**Added spec-specific helpers:**
- `add_skill_deliverables()`, `add_skill_resource_deliverable()`, `add_skill_script_deliverable()`, `add_skill_template_deliverable()`
- `add_mcp_deliverables()`, `add_mcp_tool_deliverable()`
- `add_hook_deliverables()`
- `add_command_deliverables()`
- `add_agent_deliverables()`
- `add_persona_deliverables()`
- `add_plugin_deliverables()`
- `add_flight_deliverables()`, `add_flight_step_deliverable()`
- `add_metastack_deliverables()`, `add_metastack_field_deliverable()`
- `add_automation_deliverables()`

**Updated `/tmp/paia-builder/paia_builder/utils.py`:**
- Exports all new giint functions
- Marked legacy functions as deprecated

### Still TODO (CRITICAL)

1. **Update core.py** - each `add_*` method must call both:
   - paia-builder model update (already does)
   - giint project building (needs to call `add_component()` + `add_*_deliverables()`)

2. **Add interactive field methods** - for EACH field in EACH spec:
   - `set_skill_md(skill_name, content)` → updates SkillSpec.skill_md + completes giint task
   - `set_skill_reference(skill_name, content)` → updates SkillSpec.reference_md + completes giint task
   - `add_skill_resource(skill_name, resource)` → appends to resources + adds giint deliverable
   - Same pattern for ALL specs

3. **Rename DeliverableSpec** → `PAIACompiler` (it's a compiler, not a giint deliverable)

4. **Test end-to-end** - build a skill interactively, verify giint project has correct hierarchy

### The Pattern (for future sessions)

Each paia-builder add_* method should:
```python
def add_skill(self, name, domain, category, description):
    # 1. Create spec
    spec = utils.create_skill_spec(name, domain, category, description)
    
    # 2. Add to paia model
    paia.skills.append(spec)
    
    # 3. Create giint component
    utils.add_component(paia.name, "skills", name)
    
    # 4. Add standard deliverables
    utils.add_skill_deliverables(paia.name, name)
    
    # 5. Attach spec JSON
    utils.attach_spec_to_component(paia.name, "skills", name, spec.model_dump(), paia.git_dir)
```

Each field setter should:
```python
def set_skill_md(self, skill_name, content):
    # 1. Find spec and update
    spec = find_skill(paia, skill_name)
    spec.skill_md = content
    
    # 2. Complete giint task
    utils.complete_task(paia.name, "skills", skill_name, "skill_md", "create_skill_md")
```

### Files Changed
- `/tmp/paia-builder/paia_builder/util_deps/giint_ops.py` - complete rewrite
- `/tmp/paia-builder/paia_builder/utils.py` - updated exports

### Key Insight

giint projects are built INTERACTIVELY. Each add_* call in paia-builder must call the corresponding giint add_* functions. The hierarchy IS the spec - you build it piece by piece, and each piece maps to a giint deliverable with tasks.

### COMPLETED THIS SESSION

**core.py updated:**
- `_after_add()` now calls interactive giint building (not auto-generation)
- All `add_*` methods pass spec to `_after_add()` for attachment
- Pattern: add_component → add_*_deliverables → attach_spec_to_component

**Files changed:**
- `/tmp/paia-builder/paia_builder/util_deps/giint_ops.py` - complete rewrite
- `/tmp/paia-builder/paia_builder/utils.py` - new exports
- `/tmp/paia-builder/paia_builder/core.py` - _after_add + all add_* methods

**Remaining for next session:**
1. Add field setters (set_skill_md, add_skill_resource, etc.) that complete giint tasks
2. Rename DeliverableSpec → PAIACompiler
3. Test end-to-end with real giint project

---

## SESSION: 2026-01-16 - Field Setters Complete

### What Was Done

**Added 13 field setter methods to core.py:**
- Skill: `set_skill_md()`, `set_skill_reference()`, `add_skill_resource()`, `add_skill_script()`, `add_skill_template()`
- MCP: `set_mcp_server()`, `add_mcp_tool()`
- Hook: `set_hook_script()`
- Command: `set_command_prompt()`
- Agent: `set_agent_prompt()`
- Persona: `set_persona_frame()`
- Flight: `add_flight_step()`
- Metastack: `add_metastack_field()`
- Automation: `set_automation_workflow()`, `set_automation_webhook()`
- Plugin: `set_plugin_manifest()`

**Pattern for each setter:**
```python
def set_skill_md(self, skill_name: str, content: str) -> str:
    paia = self._ensure_current()
    spec = utils.find_component(paia, "skills", skill_name)
    if not spec:
        return f"[HIEL] Skill '{skill_name}' not found."
    spec.skill_md = content
    spec.updated = datetime.now()
    self._save(paia)
    if utils.GIINT_AVAILABLE and paia.git_dir:
        utils.complete_task(paia.name, "skills", skill_name, "skill_md", "create_skill_md")
    return f"[VEHICLE] Skill '{skill_name}' SKILL.md set."
```

**Renamed DeliverableSpec → PAIACompiler:**
- PAIACompiler is the compilation machinery
- DeliverableSpec kept as alias for backwards compatibility
- Clear separation from giint's Deliverable concept

### Files Changed
- `/tmp/paia-builder/paia_builder/core.py` - Added 13 field setters
- `/tmp/paia-builder/paia_builder/models.py` - Renamed DeliverableSpec → PAIACompiler

### Tests Passed
- pip install succeeds
- All field setters exist and are callable
- PAIACompiler exported, DeliverableSpec is alias
- giint utils properly exported

### Architecture Now Complete
```
paia-builder add_* methods → creates spec + giint component + deliverables
paia-builder set_* methods → updates field + completes giint task
giint project hierarchy mirrors paia-builder model hierarchy
```

---

## SESSION: 2026-01-16 - Events ↔ GEAR Clarification

### What "Events → GEAR" Actually Means

The original note was ambiguous. Clarified understanding:

**Events is the message bus between GEAR and Frontend (Railgun)**

Bidirectional:
```
GEAR ←→ Events ←→ Frontend (Railgun)

GEAR changes → emit event → SSE → frontend displays current state
User accepts/rejects → frontend event → updates GEAR proof
```

**NOT** "runtime events update GEAR scores"
**IS** "GEAR pushes state to frontend, frontend pushes user decisions back"

### Why This Matters

Frontend is where user provides **proof**:
- "I accept this component" → G proof (gear exists)
- "This is published" → A proof (achievement validated)
- "This actually changed something" → R proof (reality grounded)

GEAR's proof semantics require user confirmation. Events system is how that flows.

### Implementation Needed

1. **GEAR → Events**: When GEAR state changes, emit event for SSE to frontend
2. **Events → GEAR**: Frontend user actions (accept/reject) come back as events that update GEAR proof

### Files Involved
- `harness/core/event_router.py` - already routes to SSE
- `paia-builder/models.py` - GEAR model
- Frontend (Railgun) - needs to send acceptance events back

---

## SESSION: 2026-01-16 - GEAR ↔ Events Bidirectional Bus IMPLEMENTED

### What Was Done

**Created `harness/events/gear_events.py`:**
- `GEAREventType` enum with outbound (gear_state_changed, dimension_updated, level_up, tier_advanced, golden_changed) and inbound (component_accepted, achievement_validated, reality_grounded, proof_rejected) event types
- `GEARDimensionType` enum (gear, experience, achievements, reality)
- `gear_event()` builder function for creating GEAR events
- Outbound emitters: `emit_gear_state()`, `emit_dimension_update()`, `emit_level_up()`, `emit_tier_advanced()`
- `GEARProofHandler` class for handling inbound acceptance events
- `AcceptanceEvent` dataclass for frontend→backend proof events

**Added HTTP endpoints to `harness/server/http_server.py`:**
- `POST /gear/accept` - Frontend sends acceptance events (G/A/R proof)
- `POST /gear/emit` - Trigger GEAR state emission to SSE
- `GET /gear/{paia_name}` - Get current GEAR state
- `POST /gear/register` - Register PAIA for tracking
- `GET /gear/list` - List registered PAIAs

**Updated exports:**
- `harness/events/__init__.py` - exports all gear_events
- `harness/__init__.py` - exports GEAR event types

### The Flow

```
OUTBOUND (GEAR → Frontend):
PAIABuilder makes changes → call emit_gear_state(router, paia_name, gear_state)
                                    ↓
                            EventRouter routes to SSE callbacks
                                    ↓
                            Frontend receives via /events SSE stream

INBOUND (Frontend → GEAR):
User accepts component → Frontend POST /gear/accept
                                    ↓
                         GEARProofHandler.handle(AcceptanceEvent)
                                    ↓
                         Updates PAIA gear_state notes/proofs
```

### Files Changed
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/events/gear_events.py` - NEW
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/events/__init__.py` - exports
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/__init__.py` - exports
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/http_server.py` - GEAR endpoints

### Still TODO
1. **Wire paia-builder to emit GEAR events** - call emit_* when GEAR changes
2. **Frontend (Railgun) integration** - consume SSE, send acceptance events
3. **Persist PAIA state** - currently in-memory cache, needs proper storage
