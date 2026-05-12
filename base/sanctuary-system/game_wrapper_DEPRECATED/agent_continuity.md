# Agent Framework Continuity Notes

## Session: 2026-01-15

### Core Architecture Decision

**CodeAgent(Actor)** - Base class IS a llegos Actor
- Inbox for queued messages
- Ingress points (email, sms, discord, etc) write to inbox
- Agent checks inbox on stop hook or poll
- Message passing is FUNDAMENTAL, not a PAIA add-on

### Class Hierarchy

```
CodeAgent(Actor)              # Base - any code agent, has inbox
    │
    └── ClaudeCodeAgent       # Claude-specific impl
            │                   - uses tmux (interactive, can inject messages)
            │                   - persistent session
            │                   - .config = ClaudeCodeAgentConfig
            │
            └── ClaudeCodeSubAgent  # For isolated workers
                                    - uses claude -p
                                    - own directory/config
                                    - fire-and-forget
                                    - returns via block report

PAIAAgent                     # Wraps CodeAgent
    - omnisanc state machine
    - guru loop
    - PAIA-specific behaviors
    - NOT where Actor pattern lives (that's in CodeAgent)
```

### tmux vs claude -p

| Feature | tmux | claude -p |
|---------|------|-----------|
| Interactive | YES | NO |
| Mid-flight injection | YES (send_keys) | NO |
| Isolated config | NO | YES (--mcp-config, --plugin-dir, --settings) |
| Persistent session | YES | NO (run to completion) |
| Stream events | capture_pane | --output-format stream-json |

**Main agent = tmux** (interactive, inbox works)
**Sub-agents = claude -p** (isolated, one-shot)

### claude -p Isolation

Each instance can have:
- `--mcp-config` custom MCPs
- `--plugin-dir` custom plugins
- `--settings` custom settings
- `--strict-mcp-config` ignore global

OR: project-scoped .claude/ directory per agent

**Agent = directory with .claude/ project settings**

### Block Report Pattern (for -p agents)

Since -p is one-way (can't inject mid-flight):
1. Agent runs via claude -p
2. Agent hits block -> emits structured signal (autopoiesis blocked)
3. We catch in stream-json events
4. We process, then --continue with response

This enables structured message passing without tmux.

### Framework vs PAIA Knowledge

**Framework (what we build):**
- CodeAgent(Actor) with inbox
- Message passing / ingress points
- Network coordination
- Game harness control

**PAIA knowledge (what Claude knows):**
- Use claude -p for isolated tasks
- Use tmux for interactive sessions
- Use --continue, --resume for session control
- Spawn subagents with different configs

The framework doesn't encode -p. The PAIA knows it as a tool.

### Existing Code Locations

- **llegos.py**: `/home/GOD/core/computer_use_demo/tools/base/chains/base/llegos/llegos.py`
- **HermesActor**: `/home/GOD/core/computer_use_demo/tools/base/chains/base/hermes_actor.py`
- **hermes_legos.py**: `/home/GOD/heaven-base/heaven_base/langgraph/hermes_legos.py`
- **PAIAHarness**: `/tmp/sanctuary-system/game_wrapper/core/harness.py`

### COMPLETED: CodeAgent(Actor) - Session 2026-01-15

**Files**:
- `/tmp/sanctuary-system/game_wrapper/core/agent.py` - CodeAgent implementation
- `/tmp/sanctuary-system/llegos/` - llegos as pip-installable package (LGPL-3.0)

**Setup**:
```bash
pip install svix-ksuid  # Required dep
pip install -e /tmp/sanctuary-system/llegos  # Install llegos package
```

**Implementation**:
- llegos from https://github.com/CyrusNuevoDia/llegos (LGPL-3.0)
- Packaged as `/tmp/sanctuary-system/llegos/` with src layout + pyproject.toml
- `CodeAgent(Actor)` properly extends llegos Actor
- MRO: `CodeAgent -> Actor -> Object -> BaseModel -> object`
- Priority-based inbox queue
- Message types: `InboxMessage`, `UserPromptMessage`, `SystemEventMessage`, `BlockedMessage`, `CompletedMessage`
- `receive_{message_type}` handler pattern (llegos convention)
- Event emitter, inbox persistence
- Helpers: `create_user_message()`, `create_system_event()`

**Tests passing**: enqueue, dequeue, priority ordering, handler dispatch

### COMPLETED: CodeAgent + ClaudeCodeAgent - Session 2026-01-15

**CodeAgent** (`/tmp/sanctuary-system/game_wrapper/core/agent.py`):
- Extends llegos Actor (inbox + message passing)
- tmux control: `session_exists`, `create_session`, `spawn_agent`, `send_keys`, `capture_pane`, `send_and_wait`
- Config: `agent_command`, `tmux_session`, `response_marker`, `poll_interval`, `max_wait_seconds`

**ClaudeCodeAgent** (same file):
- Extends CodeAgent
- Just sets defaults: `tmux_session="claude"`, `response_marker="◇"`
- User still provides `agent_command="claude"` in config

**Architecture:**
- Game harness → tmux → ONE interactive agent
- NO `-p` in framework - that's PAIA knowledge

### COMPLETED: Integration Test - Session 2026-01-15

**HTTP Server + Harness Integration WORKING**

Test flow:
```bash
# Start server
cd /tmp/sanctuary-system && uvicorn game_wrapper.server.http_server:app --host 127.0.0.1 --port 8765

# Spawn Claude in separate tmux session
curl -X POST http://127.0.0.1:8765/spawn -H "Content-Type: application/json" \
  -d '{"agent_command": "claude", "working_directory": "/tmp"}'

# Send prompt and get response
curl -X POST http://127.0.0.1:8765/send -H "Content-Type: application/json" \
  -d '{"prompt": "list 3 colors", "timeout": 60}'
# Returns: {"response": "● ☀️🌏💗🌐\n\n  Red, blue, green.\n\n───", "prompt": "list 3 colors"}
```

**Bugs Fixed:**
- `send_keys()` takes list, not varargs: `send_keys([text, "Enter"])`
- `response_marker` changed from `◇` to `❯` (Claude Code prompt marker)
- Response extraction: find content between last two `❯` markers

**Response Extraction Logic:**
```python
marker_indices = [i for i, line in enumerate(lines)
                 if line.strip().startswith("❯")]
# Response = lines[marker_indices[-2]+1 : marker_indices[-1]]
```

### Next Steps

1. ~~CodeAgent(Actor) with inbox~~ ✓ DONE
2. ~~tmux runner methods~~ ✓ DONE
3. ~~ClaudeCodeAgent~~ ✓ DONE
4. ~~IngressType enum~~ ✓ DONE (MVP: FRONTEND only)
5. ~~MVP: `/send` → `send_and_wait()`~~ ✓ DONE - Integration test passing
6. (Optional) b64 encoding for special chars in prompts
7. Integrate CodeAgent into harness (replace PAIAHarness duplicate tmux methods)
8. Future: Wire inbox for async multi-ingress scenarios
9. (Future) Heaven -> Claude Code compatibility

### DISCOVERED: PAIA Builder Already Exists!

**Location**: `/tmp/paia-builder/`

```
/tmp/paia-builder/
├── CONTINUITY.md      # 14KB of context!
├── paia_builder/      # The actual code
├── pyproject.toml
└── setup.py
```

**The Full Tower (from CartON):**
```
Infoproduct Layer → Progression Layer (GEAR) → Builder Layer (PAIA Builder)
→ Generation Layer (context engineering) → Runtime Layer (gnosys-plugin)
→ Base Layer (Code Agent)
```

**What We Built Today:**
- CodeAgent(Actor) = Base Layer ✅
- ClaudeCodeAgent = Runtime specialization ✅
- Integration test = HTTP → tmux → Claude ✅

**What's Next:**
- READ `/tmp/paia-builder/CONTINUITY.md` - has full context
- READ `/tmp/paia-builder/paia_builder/` - existing implementation
- Integrate or build on existing work

**Meta-interpreter Hierarchy:**
```
L1 (Substrate):    CodeAgent       = raw computation
L2 (Wrapper):      PAIAAgent       = PAIA behaviors (omnisanc, guru)
L3 (REPL):         GNOSYS          = reified instance
                      ↓
                   UserPAIA        = user's custom PAIA
                   (inherits GNOSYS or PAIAAgent)
```

### CartON Reference

Observation captured: `20260115_161318_d2162624.json`
Concepts: PAIA_Agent_Class_Hierarchy, Claude_P_Isolation_Discovery, Tmux_Vs_Claude_P_Tradeoff
Related: Complete_Paia_Infoproduct_Stack, Homoiconic_Meta_Interpreter_Layers

---

## Session: 2026-01-15 (continued after compaction)

### PAIA Builder Analysis Complete

**paia-builder** (`/tmp/paia-builder/`) is the **Builder Layer** - tracks components, GEAR progression, generates CLAUDE.md.

**CodeAgent** is the **Runtime Layer** - tmux control, message passing, actor model.

**These are COMPLEMENTARY, not duplicates.**

### Full Architecture: Container-Based Agent Deployment

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: DESIGN (on host)                                  │
│  User + GNOSYS → paia-builder → PAIA Blueprint              │
│  (doesn't have to be L13 - any target level)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    bake_paia.sh <paia-name>
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: BAKE                                              │
│  Docker image with PAIA baked in                            │
│  (CLAUDE.md, paia.json, components, configs)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    docker run paia-<name>
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  CONTAINER                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  tmux session                                        │   │
│  │  └── PAIAAgent (self-leveling via stop hook stack)  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  State files (GEAR, stop hook stack, inbox)         │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  HTTP/WebSocket server (monitoring endpoint)        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────┐
│  HOST: Game Harness                                         │
│  - Read state files (mounted volume or websocket)           │
│  - Attach tmux for manual intervention                      │
│  - Monitor stop hook stack                                  │
└─────────────────────────────────────────────────────────────┘
```

### PAIAAgent Architecture

**PAIAAgent = CodeAgent + Blueprint + GEAR (instance state)**

```python
class PAIAAgent(CodeAgent):
    blueprint: PAIA          # Target state (from paia-builder)
    gear: GEAR               # Current instance state
    builder: PAIABuilder     # Can modify its own blueprint as it works

    def level_gap(self) -> int:
        return self.blueprint.gear_state.level - self.gear.level

    def work_toward_blueprint(self):
        # Look at what blueprint says I should have
        # Look at what I actually have
        # Do work to close the gap
        # Earn XP, advance tiers, goldify components
```

**Self-Leveling Agent**: Blueprint says "Level N", instance is at "Level X", agent's job is to close the gap (X → N) via stop hook stack autonomy.

### What paia-builder Provides

- 16 component types: skills, mcps, hooks, commands, agents, personas, plugins, flights, metastacks, giint_blueprints, operadic_flows, frontend_integrations, automations, agent_gans, agent_duos, system_prompts
- GEAR progression (Grind, Experience, Achievement, Reality)
- Tier advancement: none → common → uncommon → rare → epic → legendary
- Golden status: quarantine → crystal → golden
- SOSEEH thematization: [PILOT], [VEHICLE], [MISSION CONTROL], [LOOPS]
- `check_win()` generates CLAUDE.md when PAIA is constructed

### Pieces to Build

1. **PAIAAgent class** - extends CodeAgent + blueprint + instance GEAR
2. **bake_paia.sh** - takes paia name, builds Docker image from blueprint
3. **Dockerfile template** - base image + PAIA-specific layers
4. **Container entrypoint** - starts PAIAAgent in tmux with stop hook stack
5. **State file protocol** - what files, where, format (for host monitoring)
6. **WebSocket server** - optional real-time monitoring from host to container
7. **GNOSYS reification** - concrete PAIAAgent instance that can spawn others

### The Integration Point

```
paia-builder.check_win() == True
    ↓ outputs
git_dir/CLAUDE.md + paia.json
    ↓ baked into
Docker image
    ↓ runs
PAIAAgent in container
    ↓ levels up via
Stop hook stack (autopoietic autonomy)
```

### PAIA Compilation Pattern (Detailed)

**Blueprint vs Compilation:**
- PAIABlueprint = SPEC (what the PAIA should have)
- Compilation = Agent REALIZES spec into actual files
- Evolved Image = COMPILED PAIA
- Library Class = SDK entry point

**The Flow:**
```
PAIABlueprint (spec in paia-builder)
    ↓ bake into
Seed Docker Image (container with blueprint + system prompt)
    ↓ docker run
Agent EXECUTES blueprint:
    - Creates actual code files (skills/, mcps/, hooks/)
    - Updates system prompt as it builds
    - Uses paia-builder to TRACK progress (not add components)
    - Works in the dir it will package from
    - Forks from its own container (already set up)
    ↓ AI thinks done
check_win() → triggers docker commit
    ↓ Human scores
    ├── Accept → Canonical
    │       ↓
    │   Auto-codegen class in library
    │       ↓
    │   Repackage library
    │       ↓
    │   Update frontend catalog (railgun loads this image)
    │
    ├── Continue → Same container, guru loop continues
    │
    └── Restart → New container, different prompt
```

**GNOSYS Bootstrap:**
1. Hand-craft minimal GNOSYS PAIABlueprint
2. Run compilation process
3. GNOSYS builds itself (creates actual code files)
4. Commits as evolved image
5. Auto-codegen as `GNOSYS` class in library
6. Repackage library with new class
7. New image in compose group
8. Deploy to Discord (Patreon access)

**Key Distinctions:**
- `paia-builder.add_*()` = Design phase (define what PAIA should have)
- Agent execution = Compilation phase (create actual code from spec)
- `check_win()` = Compilation complete signal
- Human scoring = QA gate before canonical

### COMPLETED: PAIAAgent Class - Session 2026-01-15

**File**: `/tmp/sanctuary-system/game_wrapper/core/paia_agent.py`

**PAIAAgent** extends CodeAgent with:
- `_blueprint` - PAIA model loaded from paia.json
- `_compilation` - CompilationState tracking created files/components
- `_builder` - PAIABuilder reference for tracking progress

**Key Methods:**
- `_load_blueprint()` - Load PAIABlueprint from paia.json
- `start_compilation()` - Begin compilation process
- `register_created_file(path)` - Track file creation
- `register_created_component(type, name)` - Track component creation
- `get_remaining_components()` - What's left to build
- `compilation_progress()` - Progress report dict
- `check_win()` - Returns True when all components realized
- `docker_commit(tag)` - Commit container as new image
- `save_state() / load_state()` - Persist compilation state

**CompilationState** tracks:
- `started_at / completed_at` - Timestamps
- `created_files` - List of paths
- `created_components` - Dict by type

**Factory:**
```python
from game_wrapper.core.paia_agent import create_paia_agent

agent = create_paia_agent(
    blueprint_path="/path/to/paia.json",
    working_dir="/path/to/workdir",
    agent_command="claude"
)
agent.start()
```

**TODO (codenose):**
- Refactor into utils pattern (paia_agent_utils.py)
- Split docker_commit() into smaller functions
- File is 535 lines - could modularize

### Next Steps

1. ~~PAIAAgent class~~ ✓ DONE (needs refactor but functional)
2. ~~bake_paia.sh + Dockerfile~~ ✓ DONE - Docker bake pipeline
3. ~~Container entrypoint~~ ✓ DONE - entrypoint.sh with guru loop support
4. **State file protocol** - Define what host reads for monitoring
5. **GNOSYS bootstrap** - Test base image with guru loop instruction

### COMPLETED: Docker Bake Pipeline - Session 2026-01-15

**Existing Base Image**: `paia-agent:latest` (from `/home/GOD/heaven/orchestrator/`)
- Claude CLI + tmux + handoff server (FastAPI)
- Already has /execute endpoint, inbox injection, orchestrator communication

**All Docker files consolidated**: `/tmp/sanctuary-system/game_wrapper/docker/`
- `Dockerfile.base` - Original paia-agent (Claude CLI + tmux + handoff)
- `Dockerfile.extended` - Extends paia-agent:latest with guru + MCPs
- `entrypoint-guru.sh` - Wraps base, adds guru instruction support
- `mcp-config.base.json` - Base MCPs (skillmanager, gnosys_kit, autopoiesis, self-claude)
- `requirements-base.txt` - Python dependencies
- `bake_paia.sh` - Build/run/commit script

**Usage**:
```bash
# Build base image
./bake_paia.sh base

# Run PAIA with guru instruction
./bake_paia.sh run test-paia "You are being born as a PAIA. Self-organize."

# Attach to see what's happening
./bake_paia.sh attach test-paia

# Check state (host monitoring)
./bake_paia.sh status test-paia

# Commit as evolved image
./bake_paia.sh commit test-paia gnosys:v1
```

**State File Protocol**:
- `/home/paia/state/agent_state.json` - Status, heartbeat, session info
- `/home/paia/state/guru_instruction.txt` - Initial instruction
- Host mounts `/tmp/paia-state/<name>/` to monitor

### COMPLETED: GNOSYS Bootstrap Instruction - Session 2026-01-15

**File**: `/tmp/sanctuary-system/docker/guru-instructions/gnosys-bootstrap.md`

**Usage**:
```bash
# Bootstrap GNOSYS from base image
./bake_paia.sh run gnosys "@guru-instructions/gnosys-bootstrap.md"

# Watch it self-organize
./bake_paia.sh attach gnosys

# When ready, commit
./bake_paia.sh commit gnosys gnosys:v1
```

**The Bootstrap Pattern**:
1. Base image = Claude Code + base MCPs (empty state)
2. Guru instruction tells agent: "You are GNOSYS. Self-organize."
3. Agent explores tools, creates skills, uses autopoiesis
4. Agent builds its own knowledge/state
5. Human scores → commit → evolved image
6. Next instantiation starts with evolved state

### Ready for Testing

All pieces in place:
- PAIAAgent class (runtime)
- Docker bake pipeline (containerization)
- GNOSYS bootstrap instruction (differentiation)

Test sequence:
1. `./bake_paia.sh base` - Build base image
2. `./bake_paia.sh run gnosys "@guru-instructions/gnosys-bootstrap.md"`
3. Attach and observe self-organization
4. Score and commit if successful

### COMPLETED: Smoke Test - Session 2026-01-15

**Container `paia-smoke-test` running:**
- Built `paia/extended:latest` from `paia-agent:latest`
- tmux session "claude" active
- Handoff server on port 8421
- State files in `/tmp/paia-state/smoke-test/`
- User did Claude auth manually (required for each new PAIA)

**Commands:**
```bash
cd /tmp/sanctuary-system/game_wrapper/docker
./bake_paia.sh attach smoke-test  # Attach to Claude
./bake_paia.sh status smoke-test  # Check state
docker logs paia-smoke-test       # View logs
docker stop paia-smoke-test       # Stop when done
```

**Next: Full compilation test with real guru instruction**

**Port Mapping Note:**
- Command server exposed on host at `localhost:8421`
- Frontend (on host) can reach it
- Container-to-container needs Docker network or IP (172.17.0.x)
- bake_paia.sh now auto-assigns ports starting from 8421

**Command Server Endpoints:**
- `/interrupt` POST - Send ESC (cancel operation)
- `/exit` POST - Types /exit (graceful)
- `/force_exit` POST - Ctrl+C
- `/kill_agent_process` POST - pkill claude (keeps tmux)
- `/claude/start` POST - Start Claude with prompt
- `/execute` POST - Run bash/python
- `/health` GET - Health check

### Session 2026-01-15 Late: SkillSpec + YOUKNOW Discovery

**SkillSpec fixed** in `/tmp/paia-builder/paia_builder/models.py`:
- Now describes actual build structure (skill_md, reference_md, resources, scripts, templates)
- Path is DERIVED, not specified
- Enables YOUKNOW validation: spec → build → observe → ontology errors

**YOUKNOW kernel** at `/tmp/youknow_kernel_current/`:
- Bijective hallucination detector
- Shows missing morphisms when claims don't match structure
- Outputs to OWL ontology
- The "crystal ball" that validates what PAIAs think they know

**The loop:** Spec defines shape → PAIA builds → CartON observes → YOUKNOW validates → Ontology errors if mismatch

**Next:** Fix remaining 15 component specs (MCPSpec, HookSpec, etc.) same pattern
