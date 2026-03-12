# Full Loop Stack Manifest

Files for the KG system to read to understand the complete OMNISANC + Guru + Autopoiesis stack.

---

## 1. AUTOPOIESIS LOOP STACK (Core)

### Hooks (the actual runtime)
- `/tmp/autopoiesis_mcp/hooks/brainhook.py` - L0: Reflection loop, blocks Stop
- `/tmp/autopoiesis_mcp/hooks/metabrainhook.py` - TOP: Orchestration mode, UserPromptSubmit injection
- `/tmp/autopoiesis_mcp/hooks/autopoiesis_stop_hook.py` - L1: Promise enforcement
- `/tmp/autopoiesis_mcp/hooks/hooks.json` - Hook configuration

### Commands (user interface)
- `/tmp/autopoiesis_mcp/commands/brainhook.md` - Toggle brainhook
- `/tmp/autopoiesis_mcp/commands/metabrainhook.md` - Toggle metabrainhook orchestration
- `/tmp/autopoiesis_mcp/commands/guru.md` - Start guru loop (bodhisattva vow)
- `/tmp/autopoiesis_mcp/commands/guru-pause.md` - Pause guru
- `/tmp/autopoiesis_mcp/commands/guru-resume.md` - Resume guru

### MCP Server
- `/tmp/autopoiesis_mcp/autopoiesis_mcp/mcp_server.py` - Autopoiesis MCP

### Design Docs (philosophy + architecture)
- `/tmp/autopoiesis_mcp/supertask_design/01_problem_statement.md`
- `/tmp/autopoiesis_mcp/supertask_design/02_achilles_tortoise.md`
- `/tmp/autopoiesis_mcp/supertask_design/03_sycophancy_hijack.md`
- `/tmp/autopoiesis_mcp/supertask_design/04_absolution_gate.md`
- `/tmp/autopoiesis_mcp/supertask_design/05_llm_meditation.md`
- `/tmp/autopoiesis_mcp/supertask_design/06_rakshasa_binding.md`
- `/tmp/autopoiesis_mcp/supertask_design/07_implementation.md`
- `/tmp/autopoiesis_mcp/supertask_design/08_three_level_architecture.md`
- `/tmp/autopoiesis_mcp/supertask_design/09_evolution_arc.md`
- `/tmp/autopoiesis_mcp/supertask_design/10_construction_phases.md`
- `/tmp/autopoiesis_mcp/supertask_design/11_meta_brainhook_architecture.md` - KEY: metabrainhook as daemon
- `/tmp/autopoiesis_mcp/supertask_design/12_paia_control_plane.md`
- `/tmp/autopoiesis_mcp/supertask_design/13_swarm_orchestrator_vision.md`
- `/tmp/autopoiesis_mcp/supertask_design/rakshasa-method.md`

### Config Files (runtime state)
- `/tmp/metabrainhook_state.txt` - on/off toggle
- `/tmp/brainhook_state.txt` - on/off toggle
- `/tmp/heaven_data/metabrainhook_config.json` - orchestration config

---

## 2. OMNISANC (State Machine / Journey System)

### Core Implementation
- `/home/GOD/.claude/hooks/omnisanc_core.py` - Core state machine
- `/home/GOD/.claude/hooks/omnisanc_router.py` - Hook router
- `/home/GOD/.claude/hooks/omnisanc_home.py` - Home mode logic
- `/home/GOD/.claude/hooks/omnisanc_validator.py` - Validation
- `/home/GOD/omnisanc_core_daemon/omnisanc_logic.py` - Daemon logic

### gnosys-plugin version
- `/tmp/gnosys-plugin/hooks/omnisanc_core.py`
- `/tmp/gnosys-plugin/hooks/omnisanc_router.py`
- `/tmp/gnosys-plugin/omnisanc_core_daemon/omnisanc_logic.py`

### State Definitions
- `/tmp/sanctuary-revolution/sanctuary_revolution/omnisanc_state.py` - OmnisancPhase enum

### Docs
- `/tmp/sanctuary-revolution-treeshell/docs/omnisanc_state_machines.md`
- `/tmp/sanctuary-revolution-treeshell/docs/omnisanc_queue_spec.md`

### Registries (runtime data)
- `/tmp/heaven_data/registry/omnisanc_phases_registry.json`
- `/tmp/heaven_data/registry/omnisanc_flows_registry.json`
- `/tmp/heaven_data/registry/omnisanc_flowchains_registry.json`
- `/tmp/heaven_data/registry/omnisanc_sequences_registry.json`
- `/tmp/heaven_data/registry/omnisanc_validation_rules_registry.json`

---

## 3. STARSYSTEM (Navigation Layer)

### Starsystem MCP (wrapper)
- `/home/GOD/starsystem-mcp/starsystem/starsystem_mcp.py` - Main MCP
- `/home/GOD/starsystem-mcp/starsystem/mission.py` - Mission logic
- `/home/GOD/starsystem-mcp/starsystem/mission_types.py` - Mission types

### Starship MCP (flight configs)
- `/home/GOD/starship_mcp/starship/mcp_server.py`
- `/home/GOD/starship_mcp/starship/core.py`

### Starlog MCP (session tracking)
- `/home/GOD/starlog-mcp/starlog/mcp_server.py`
- `/home/GOD/starlog-mcp/starlog/core.py`

### Waypoint MCP (step-by-step flight execution)
- Location in starsystem or separate

---

## 4. GLOBAL RULES (Persistent Memory)

- `/home/GOD/.claude/rules/full-ship-plan.md` - Complete ship plan
- `/home/GOD/.claude/rules/autopoiesis-priority.md` - Current priority
- `/home/GOD/.claude/rules/sanctuary-journey-architecture.md` - Journey modes
- `/home/GOD/.claude/rules/sanctuary-dirs.md` - Directory map
- `/home/GOD/.claude/rules/rakshasa-method.md` - Bodhisattva pattern
- `/home/GOD/.claude/rules/omnisanc-treeshell.md` - OMNISANC → TreeShell mapping

---

## 5. SANCTUARY REVOLUTION (Game Layer)

### Specs
- `/tmp/launch_v0/roadmap_complete_jan18/WORKING_SPEC.md` - Complete architecture
- `/tmp/launch_v0/roadmap_complete_jan18/DIRECTORY_MAP.md` - Directory relationships

### Game Implementation
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/http_server.py` - Central brain
- `/tmp/sanctuary-revolution/sanctuary_revolution/harness/core/agent.py` - CodeAgent class

---

## THE STACK (Conceptual)

```
metabrainhook (TOP - orchestration daemon, can't self-disable)
    ↓ spawns/configures
guru loop (L2 - bodhisattva vow, requires emanation)
    ↓ gates via
samaya gate (verification before exit)
    ↓ contains
autopoiesis (L1 - promise level, task completion)
    ↓ contains
brainhook (L0 - reflection, "look again")

OMNISANC runs PARALLEL to this:
- HOME mode = no course plotted, metabrainhook active
- JOURNEY mode = course plotted, mission active
  - STARPORT → LAUNCH → SESSION → LANDING → MISSION cycle
  - During SESSION: autopoiesis/guru loops operate
```

---

## KEY INSIGHT

During HOME mode:
- metabrainhook is active (orchestration)
- User can plot course → starts MISSION
- Enters JOURNEY mode

During JOURNEY mode:
- OMNISANC state machine controls zones
- Inside SESSION: guru loop operates
- autopoiesis ensures task completion
- brainhook ensures reflection

guru runs ABOVE the navigation - it's the meta-loop that ensures quality work regardless of which OMNISANC zone you're in.
