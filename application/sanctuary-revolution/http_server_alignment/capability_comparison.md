# Capability-Level Comparison: CAVE vs SANCREV HTTP Servers

> **Source data**:
> - CAVE: `/tmp/sanctuary-revolution/http_server_alignment/cave_server_deep_callgraphs.md`
> - SANCREV: `/tmp/sanctuary-revolution/http_server_alignment/sancrev_server_deep_callgraphs.md`
>
> This comparison maps what each server can ACTUALLY DO at the subprocess/stdlib/library level — not what endpoints exist.

---

## 1. SHARED UNDERLYING CAPABILITIES

These are capabilities BOTH servers have at the subprocess/stdlib level, regardless of how many endpoints wrap them.

### 1.1 tmux Session Control via subprocess

Both servers execute tmux commands through a single chokepoint method:
- CAVE: `CodeAgent._run_tmux()` → `subprocess.run(["tmux", ...])` (agent.py:216)
- SANCREV: `PAIAHarness._run_tmux()` → `subprocess.run(["tmux", ...])` (harness.py:102)

**Shared tmux operations:**

| tmux Command | CAVE Method | SANCREV Method |
|-------------|------------|----------------|
| `tmux has-session -t {s}` | `CodeAgent.session_exists()` agent.py:221 | `PAIAHarness.session_exists()` harness.py:107 |
| `tmux new-session -d -s {s} -c {dir}` | `CodeAgent.create_session()` agent.py:229 | `PAIAHarness.create_session()` harness.py:112 |
| `tmux send-keys -t {s} {text}` | `CodeAgent.send_keys()` agent.py:254 | `PAIAHarness.send_keys()` harness.py:154 |
| `tmux capture-pane -t {s} -p -S -{n}` | `CodeAgent.capture_pane()` agent.py:265 | `PAIAHarness.capture_pane()` harness.py:188 |
| `tmux display-message -t {s} {msg}` | `TUIMixin.display_message()` tui.py | `TerminalUI._show_flash_notification()` terminal_ui.py:184 |

**The send-keys collapse**: Sancrev has 7 endpoints that ALL resolve to `subprocess.run(["tmux", "send-keys", ...])` with different arguments:

| Sancrev Endpoint | Keys Sent | Extra Orchestration |
|-----------------|-----------|---------------------|
| `POST /send` | `{user_prompt}` + `Enter` | + polling loop (capture_pane until stable) |
| `POST /interrupt` | `Escape` (1x or 2x) | None |
| `POST /exit` | `/exit` + `Enter` | None |
| `POST /force_exit` | `C-c` | None |
| `POST /self/inject` | `{message}` + `Enter` | Via bash script → subprocess |
| `POST /self/compact` | `/compact` | Via bash script → subprocess |
| `POST /self/restart` | `/exit` → wait → `claude` → `/resume` → `{post_msg}` | Via nohup bash script (background process, pgrep wait loop) |

CAVE exposes the same underlying primitive via `POST /input` and `POST /command` — both call `CodeAgent.send_keys()`. One capability, different typed wrappers.

### 1.2 Hook Enable/Disable Toggle (File-Based JSON)

Both have file-based hook control:
- CAVE: `HookControl` reads/writes `/tmp/hook_control.json` (hook_control.py:34)
- SANCREV: `HookControl` reads/writes `/tmp/hook_config.json` (hook_control.py:34)

Underlying: `pathlib.Path.read_text()` → `json.loads()` → modify dict → `json.dumps()` → `Path.write_text()`

### 1.3 Agent Registry (In-Memory Dict of Pydantic Models)

Both maintain in-memory dicts of registered agents:
- CAVE: `CAVEAgent.agent_registry` dict of `AgentRegistration` pydantic models (AgentRegistryMixin)
- SANCREV: `_agent_registry` module-level dict of `AgentRegistration` pydantic models (http_server.py:1171)

Underlying: Python dict operations + pydantic `model_dump()`

### 1.4 SSE Event Stream (asyncio.Queue → StreamingResponse)

Both use the same pattern:
- CAVE: `SSEMixin` — `asyncio.Queue(maxsize=1000)`, `_emit_event()` puts events, `event_generator()` yields as SSE (sse.py)
- SANCREV: `_event_queue = asyncio.Queue()`, `event_generator()` yields as SSE (http_server.py:152)

Underlying: `asyncio.Queue.put_nowait()` → `asyncio.Queue.get()` → `json.dumps()` → `yield f"data: {json}\n\n"`

### 1.5 CodeAgent / llegos Actor Model

Both import the same `CodeAgent` class from the same location:
- CAVE: `cave.core.agent.CodeAgent` extends `llegos.Actor` (agent.py:148)
- SANCREV: `sanctuary_revolution.harness.core.agent.CodeAgent` extends `llegos.Actor` (agent.py)

Both have: inbox (`collections.deque`), message types (`InboxMessage`, `UserPromptMessage`, `SystemEventMessage`, `BlockedMessage`, `CompletedMessage`), tmux control, event emitting via `pyee.EventEmitter`.

llegos transitive deps (shared): `beartype`, `deepmerge`, `ksuid`, `networkx`, `pydantic`, `pydash`, `pyee`, `sorcery`

### 1.6 FastAPI HTTP Server

Both use `fastapi.FastAPI` with `uvicorn` ASGI server. Both use `starlette.responses.StreamingResponse` for SSE.

---

## 2. SANCREV CAPABILITIES NOT IN CAVE

For each: what is the actual underlying operation? Is it truly new code, or a typed wrapper around something CAVE already does?

### 2.1 Send-and-Wait with Polling (TRULY NEW)

**Sancrev**: `PAIAHarness.send_and_wait(prompt, timeout)` (harness.py:198)
- Captures pane before sending → sends keys → polls with `time.sleep(poll_interval)` + `capture_pane()` in a loop → detects output stability (consecutive identical captures) → extracts response between `❯` markers

**CAVE**: Has `send_keys()` (fire-and-forget) and `capture_pane()` separately, but NO poll-until-stable logic combining them. You'd have to implement the polling loop yourself.

**Underlying new code**: The polling loop with stability detection + marker extraction. The individual primitives (send_keys, capture_pane, time.sleep) all exist in CAVE.

### 2.2 Named Self-Command Orchestration (TYPED WRAPPERS + NEW ORCHESTRATION)

**Sancrev**: `SelfCommandGenerator` (self_command_generator.py) generates bash scripts that call tmux send-keys with specific sequences.

| Operation | New Code Beyond send-keys |
|-----------|--------------------------|
| `execute_restart()` | Generates bash script with: send `/exit` → pgrep wait loop → send `claude` → send `/resume` → send post-restart message. Runs via `nohup` + `subprocess.Popen(start_new_session=True)` for background execution. |
| `execute_compact()` | Generates bash script, runs via `subprocess.run(["bash", "-c", script])` |
| `execute_inject()` | Same bash script pattern |

**CAVE**: Can send any keys via `CodeAgent.send_keys()` but has NO bash script generation, NO background process spawning (`nohup`/`Popen`), and NO multi-step orchestrated sequences with wait loops between steps.

**Underlying new code**: Bash script generation (`str` building), `subprocess.Popen` with `start_new_session=True`, `nohup` background execution, `pgrep` wait loops. The send-keys primitive is shared, but the orchestration layer is new.

### 2.3 Direct Code Execution (TRULY NEW)

**Sancrev**: `POST /execute` (http_server.py:425)
- `subprocess.run([sys.executable, "-c", code])` for Python
- `subprocess.run(["bash", "-c", code])` for Bash
- With configurable timeout

**CAVE**: Has NO direct code execution endpoint. Can only run code via hook scripts (`subprocess.run(["python3", script_path])`) or by sending keys to the tmux session.

**Underlying new code**: Direct `subprocess.run` with arbitrary user code + timeout parameter.

### 2.4 Process Kill (TRULY NEW)

**Sancrev**: `POST /kill_agent_process` (http_server.py:495)
- `subprocess.run(["sh", "-c", "ps aux | grep '[c]laude' | awk '{print $2}'"])` → `subprocess.run(["kill", "-9", pid])`

**CAVE**: Has `CodeAgent.kill_session()` (tmux kill-session) but NO process-level kill. Cannot `kill -9` individual processes.

**Underlying new code**: `ps aux | grep | awk` pipeline + `kill -9`.

### 2.5 Persona Control (TRULY NEW — simple file I/O)

**Sancrev**: `PersonaControl` (persona_control.py)
- `Path("/tmp/active_persona").write_text(name)` — activate
- `Path("/tmp/active_persona").unlink()` — deactivate
- `Path("/tmp/active_persona").read_text()` — query

**CAVE**: Has NO persona file reading/writing.

**Underlying new code**: 3 pathlib operations on `/tmp/active_persona`. Trivial to add.

### 2.6 Domain Builder Integration (TRULY NEW — external packages)

**Sancrev** imports and wraps three external builder packages:

**CAVEBuilder** (`/tmp/cave-builder/cave_builder/core.py`):
- Underlying: `pathlib.Path.glob("*.json")` + `pydantic.model_validate_json()` + `Path.write_text()` + `json.loads/dumps`
- Models: `CAVE`, `ValueLadder`, `Offer`, `Journey`, `Framework`
- Storage: JSON files in `/tmp/heaven_data/caves/`

**SANCTUMBuilder** (`/tmp/sanctum-builder/sanctum_builder/core.py`):
- Underlying: Same pathlib + pydantic + json pattern
- Models: `SANCTUM`, `LifeDomain`, `RitualSpec`, `GoalSpec`
- Storage: JSON files in `/tmp/heaven_data/sanctums/`

**PAIABuilder** (`/tmp/paia-builder/paia_builder/core.py`):
- Underlying: Same pattern + optional GIINT MCP calls + optional `shutil.copy`
- Models: `PAIA`, `GEAR`, `SkillSpec`, `MCPSpec` — inherit from `youknow_kernel.PIOEntity`
- Storage: JSON files in PAIA storage dir
- 30+ PAIAB endpoints for component CRUD, tier management, goldification, GEAR state

**CAVE**: Has NONE of these. Pure infrastructure layer with no domain modeling.

**Underlying new code**: The builder packages themselves (pydantic models + JSON file CRUD + domain logic). All file I/O uses the same stdlib primitives CAVE already uses (pathlib, json).

### 2.7 GEAR Event System (TRULY NEW)

**Sancrev**: `gear_events.py` — Growth/Experience/Awareness/Reality progression system
- `GEARProofHandler` with handlers for: component_accepted, achievement_validated, reality_grounded, proof_rejected
- `emit_gear_state()` → `EventRouter.route()` → tmux display-message + SSE
- `AcceptanceEvent`, `GEAREventType`, `GEARDimensionType` enums
- Reads/writes PAIA store JSON (but NOTE: `/gear/accept` modifies in-memory PAIA without persisting — bug)

**CAVE**: Has NO GEAR system.

**Underlying new code**: The GEAR event types, proof handler dispatch, dimension scoring. File I/O and SSE emission use shared primitives.

### 2.8 Full llegos Messaging Exposed (NEW ENDPOINTS, SHARED LIBRARY)

**Sancrev** exposes 20+ messaging endpoints using llegos primitives that CAVE already imports but does NOT expose:

| Operation | llegos Method Used | CAVE Has the Library? |
|-----------|-------------------|----------------------|
| Send message | `UserPromptMessage()` → `agent.enqueue()` | YES (same CodeAgent) |
| Reply | `Message.reply()` → `Message.reply_to()` → `Object.lift()` | YES (llegos imported) |
| Forward | `Message.forward_to()` → `Message.forward()` → `Object.lift()` | YES (llegos imported) |
| Thread traversal | `message_chain(msg, height)` — recursive parent walk | YES (llegos imported) |
| Message history | In-memory `_message_store` dict + `_message_history` list | NO (sancrev adds these) |
| Thread aliasing | `root.metadata["thread_alias"] = alias` — walk to root, set metadata | NO (sancrev-only logic) |
| Read/Unread tracking | `_read_status` dict of sets | NO (sancrev-only data structure) |
| Inbox filtering (unread) | `_is_message_read_by()` filter on deque iteration | NO (sancrev-only logic) |

**Underlying new code**: The `_message_store` dict, `_message_history` list, `_read_status` dict, thread aliasing logic, read/unread tracking. The core llegos operations (reply, forward, chain) are already available in CAVE's imports.

### 2.9 HTTP Relay to Remote Agents (TRULY NEW)

**Sancrev**: `POST /agents/{id}/execute`, `/agents/{id}/interrupt`, `/agents/{id}/inject` (http_server.py:1216-1270)
- Looks up agent address from registry
- `httpx.AsyncClient().post(f"{reg.address}/execute", json={...})` — HTTP POST to remote container

**CAVE**: Has `RemoteAgentMixin` that spawns agents via `sdna.agent_step()` (external SDNA process), but does NOT do HTTP relay to registered agent addresses.

**Underlying new code**: `httpx.AsyncClient` HTTP calls to registered agent addresses. Different approach from CAVE's SDNA-based remote agents.

### 2.10 EventRouter (TRULY NEW — structured routing)

**Sancrev**: `EventRouter` (event_router.py:149)
- Maintains `_event_log` (list of all events)
- Routes to terminal: `TerminalUI.notify()` → `subprocess.run(["tmux", "display-message", ...])`
- Routes to SSE: callbacks to `_event_queue.put_nowait()`
- Routes to hooks: writes `pending_injection.json` to `/tmp/paia_hooks/`
- Structured `Event` model with `EventSource`, `EventOutput`, `InTerminalObject`, `HookInjection`

**CAVE**: Has `_emit_event()` (SSEMixin) which directly puts to asyncio.Queue. Has `TUIMixin` which directly calls tmux. No unified routing abstraction.

**Underlying new code**: The `EventRouter` class, `Event`/`EventSource`/`EventOutput` models, routing dispatch logic, hook injection file I/O. The terminal primitives (tmux display-message) and SSE primitives (asyncio.Queue) are shared.

### 2.11 OutputWatcher (TRULY NEW — conditional)

**Sancrev**: `OutputWatcher` (output_watcher.py, conditional via `HAS_WATCHER`)
- 9 compiled regex `PatternMatcher` objects for detecting terminal output patterns
- Emits `DetectedEvent` with `EventType` enum
- Passive: watches captured pane output, does not control agent

**CAVE**: Has NO output watching capability.

**Underlying new code**: Regex pattern compilation + matching against captured output + event emission. Uses `re` stdlib.

### 2.12 Conditional Modules: Psyche/World/System (TRULY NEW — conditional)

**Sancrev**: Three event processing modules (conditional via `HAS_MODULES`):
- `PsycheModule` — emotional/psychological event processing
- `WorldModule` — external world event processing
- `SystemModule` — system-level event processing

**CAVE**: Has NO equivalent modules. Closest is AnatomyMixin's Organs, which is a registration system not an event processor.

### 2.13 SSE Keepalive (TRIVIAL — 1 line)

**Sancrev**: `event_generator()` has `asyncio.wait_for(_event_queue.get(), timeout=30.0)` with `TimeoutError` → `yield ": keepalive\n\n"`

**CAVE**: `event_generator()` blocks on `await self.event_queue.get()` with no timeout.

**Underlying new code**: One `asyncio.wait_for` wrapper + one `yield` line. Trivial.

### 2.14 CORS Middleware (TRIVIAL)

**Sancrev**: `CORSMiddleware` added to FastAPI app (http_server.py)

**CAVE**: No CORS middleware.

**Underlying new code**: One `app.add_middleware()` call.

---

## 3. CAVE CAPABILITIES NOT IN SANCREV

These are capabilities sancrev gains for free by inheriting/extending CAVE.

### 3.1 Hook Processing Pipeline (HookRouterMixin + HookRegistry + hooks.py)

**What it does**: Receives hook signals, routes them through registered hook handlers, returns results.

**Full pipeline per signal**: normalize payload (OpenClaw format) → filter by active hooks dict → get capability context from RAG → execute each matching hook → check for block responses → check DNA transition.

**Components sancrev lacks**:

| Component | What It Does | Underlying Operations |
|-----------|-------------|----------------------|
| `HookRegistry` (hooks.py:174) | Scans `cave_hooks/` dir, loads Python classes extending `ClaudeCodeHook` ABC, maintains registry dict | `pathlib.glob("*.py")` → `importlib.util.spec_from_file_location()` → `importlib.util.module_from_spec()` → `spec.loader.exec_module()` → `inspect.getmembers()` to find subclasses |
| `ClaudeCodeHook` ABC (hooks.py:56) | Abstract base class for hook handlers. `handle(payload, state) → HookResult` | Abstract method pattern |
| `ScriptHookAdapter` (hooks.py:97) | Runs external scripts as hooks via subprocess | `subprocess.run(["python3", script_path], input=json.dumps(payload))` → `json.loads(result.stdout)` |
| `HookResult` (hooks.py:18) | Typed result with `block`, `modify`, `inject`, `output` fields | Pydantic-like dataclass |
| Capability resolver (capability_resolver.py:98) | RAG-based query: extracts query from hook payload → resolves capabilities via optional `capability_predictor` module | `importlib.util.spec_from_file_location()` (lazy load) → `rag.get_capability_context()` |
| OpenClaw normalization (hook_router.py:159) | Remaps external payload format to internal format | Dict key remapping |

**Sancrev currently has**: Only `HookControl` (enable/disable toggle) — no registry, no class loading, no script execution, no processing pipeline.

### 3.2 Loop Lifecycle System (LoopManagerMixin + loops/)

**What it does**: Manages named inference loops that control what hooks are active and what prompts are sent to the agent.

**Components sancrev lacks**:

| Component | What It Does | Underlying Operations |
|-----------|-------------|----------------------|
| `AgentInferenceLoop` (loops/base.py:20) | Dataclass: name, description, prompt, active_hooks, exit_condition (callable), on_start/on_stop callbacks, next (loop or TransitionAction), conditions dict | `dataclasses.dataclass` |
| `loop.activate(cave_agent)` (loops/base.py:60) | Sets `active_hooks` on config + sends prompt via `send_keys()` | `dict.copy()` + `CodeAgent.send_keys(prompt, 0.5, "Enter")` → `subprocess.run(["tmux", "send-keys", ...])` |
| `loop.deactivate(cave_agent)` (loops/base.py:89) | Clears active_hooks + calls on_stop | `dict` clear + callback |
| `loop.check_exit(state)` (loops/base.py:110) | Evaluates exit_condition callable against hook state | `exit_condition(state)` — user-defined callable |
| `LoopManagerMixin` (loop_manager.py) | Start/stop/pause/resume/trigger API. Manages `_active_loop` and `_loop_state` | Dict operations |
| 8 predefined loops | AUTOPOIESIS (exit when `/tmp/active_promise.md` doesn't exist), GURU (exit when emanation_created in state), 6 OMNISANC loops (HOME_DAY, HOME_NIGHT, STARPORT, LAUNCH, SESSION, LANDING) | Each has specific exit_condition callable |

### 3.3 AutoModeDNA (dna.py)

**What it does**: Orchestrates sequences of loops with automatic transitions.

| Component | What It Does | Underlying Operations |
|-----------|-------------|----------------------|
| `AutoModeDNA` (dna.py:27) | Holds ordered list of `AgentInferenceLoop`s + `ExitBehavior` (one_shot/cycle) | Dataclass with list + enum |
| `dna.start(cave_agent)` (dna.py:58) | Activates first loop in sequence | `loops[0].activate(cave_agent)` |
| `dna.check_and_transition(cave_agent)` (dna.py:93) | On every hook pass: check if current loop should exit → deactivate → advance to next loop → activate | `loop.check_exit(state)` → `loop.deactivate()` → `next_loop.activate()` |
| `TransitionAction` chain (dna.py) | Optional SDNA integration: `next_target.execute_chain(lib)` using `sdna.ContextEngineeringLib` + `sdna.ActivateLoop` | `sdna` external package (optional) |

### 3.4 OMNISANC State Machine (OmnisancMixin)

**What it does**: Reads navigation state from files, computes current zone, activates appropriate hooks per zone.

| Component | What It Does | Underlying Operations |
|-----------|-------------|----------------------|
| Zone detection (omnisanc.py:57) | Reads `.course_state` JSON → computes zone: HOME / STARPORT / LAUNCH / SESSION / LANDING / MISSION | `json.loads(Path.read_text())` → Python conditional logic |
| Enable/Disable (omnisanc.py:92-118) | Toggle via presence of `.omnisanc_disabled` file | `Path.exists()` / `Path.write_text()` / `Path.unlink()` |
| Metabrainhook state (omnisanc.py:141-150) | Read/write `on`/`off` to `/tmp/metabrainhook_state.txt` | `Path.read_text().strip().lower()` / `Path.write_text()` |
| Metabrainhook prompt (omnisanc.py:179-191) | Read/write prompt JSON to `/tmp/heaven_data/metabrainhook_config.json` | `Path.read_text()` / `Path.write_text()` |
| Zone-based hook activation (cave_agent.py:242) | `run_omnisanc()` called on every hook signal → reads zone + paia_mode + auto_mode → sets `active_hooks` accordingly | File reads → dict assignment |

### 3.5 Claude State Reader (state_reader.py)

**What it does**: Reads Claude Code's filesystem configuration to provide a complete state snapshot.

| Method | Reads | Underlying Operations |
|--------|-------|----------------------|
| `read_settings()` | `~/.claude/settings.json` | `Path.exists()` → `json.loads(Path.read_text())` |
| `read_settings_local()` | `~/.claude/settings.local.json` | Same |
| `read_mcp_config()` | MCP entries from settings + settings.local + project settings | Combines reads from above |
| `read_project_state()` | `{project}/.claude/settings.json`, `{project}/.claude/rules/*.md`, `{project}/CLAUDE.md` | `Path.exists()` + `Path.glob()` + `Path.read_text()` |
| `read_hooks()` | Hook config from settings | Reads settings |
| `read_hooks_dir()` | `~/.claude/hooks/` directory | `Path.iterdir()` |
| `read_skills_dir()` | `~/.claude/skills/` directory | `Path.iterdir()` + `(item/"SKILL.md").exists()` |
| `read_global_rules()` | `~/.claude/rules/*.md` | `Path.glob("*.md")` |
| `read_plugins()` | `~/.claude/plugins/` | `Path.iterdir()` |
| `read_subagents()` | From settings JSON | `dict.get()` |
| `parse_context_pct()` | Regex on tmux captured output | `re.search(pattern, output)` |
| `get_complete_state()` | All of the above combined | Calls all methods above |

Sancrev has NO equivalent. Cannot see Claude Code's filesystem config.

### 3.6 Config Archiving/Injection (config_snapshots.py)

**What it does**: Snapshots Claude Code config files and restores them on demand.

| Method | What It Does | Underlying Operations |
|--------|-------------|----------------------|
| `archive(name)` (config_snapshots.py:89) | Copies current config files to named archive dir | `shutil.copy2(src, dst)` + `shutil.copytree(src, dst)` + metadata JSON write |
| `inject(name)` (config_snapshots.py:148) | Auto-backup current → copies archive files back to Claude Code dirs | `shutil.copy2` + `shutil.rmtree` + `shutil.copytree` |
| `list_archives()` (config_snapshots.py:209) | Enumerates archive dirs with metadata | `Path.iterdir()` + `json.loads` |
| `get_active_info()` (config_snapshots.py:240) | Detects which archive matches current via SHA256 | `hashlib.sha256()` + `Path.read_bytes()` |
| `delete_archive()` (config_snapshots.py:265) | Removes archive dir | `shutil.rmtree()` |
| `export/import_archive()` (config_snapshots.py:274-287) | Copy archives to/from external paths | `shutil.copytree()` |

Files archived: `settings.json`, `settings.local.json`, `hooks/`, `skills/`, custom config files.

### 3.7 Anatomy System (AnatomyMixin)

**What it does**: Provides Heart (scheduled execution), Blood (context carrier), and Organs (named capabilities).

| Component | What It Does | Underlying Operations |
|-----------|-------------|----------------------|
| `Heart` (anatomy.py:47) | `HeartbeatScheduler` from SDNA (optional). Schedules periodic callbacks | `sdna.HeartbeatScheduler()` — external, optional |
| `Blood` (anatomy.py:116) | Context carrier: `_payload` dict + `_flow_history` list | Dict + list operations |
| Organs (anatomy.py:181) | Named organ registry: `self.organs` dict | Dict operations |

SDNA dependency is optional — if not installed, Heart is a no-op.

### 3.8 Remote Agent Spawning via SDNA (RemoteAgentMixin + remote_agent.py)

**What it does**: Spawns remote agents using the SDNA framework.

| Component | What It Does | Underlying Operations |
|-----------|-------------|----------------------|
| `RemoteAgent` (remote_agent.py:55) | Bridges CAVE to SDNA executor | Wraps `sdna.agent_step()` |
| `agent.run(inputs)` (remote_agent.py:69) | Creates `HermesConfig` → calls `sdna.agent_step()` | `sdna.HermesConfig(...)` → `sdna.agent_step(config, inputs)` — runs `claude -p` subprocess internally |
| `RemoteAgentMixin.spawn_remote()` | Creates `RemoteAgentHandle` + emits SSE event + runs agent | Pydantic model + SSE + SDNA call |

SDNA is optional. If not installed, `spawn_remote()` returns an error response.

Note: Sancrev's HTTP relay (`httpx.AsyncClient().post()`) and CAVE's SDNA spawning are DIFFERENT approaches to the same problem (remote agent execution). They are not interchangeable.

### 3.9 PAIA State Management (PAIAStateMixin)

**What it does**: Tracks PAIA states as pydantic models with heartbeat timestamps.

| Method | What It Does | Underlying Operations |
|--------|-------------|----------------------|
| `update_paia_state(id, **data)` | Creates/updates `PAIAState` model, sets `last_heartbeat`, emits SSE | `PAIAState(pydantic)` + `setattr()` + `datetime.utcnow()` + SSE emit |
| `GET /paias` | Returns all PAIA states | Dict iteration + `model_dump()` |

Sancrev uses `PAIABuilder` + PAIA store JSON instead — different data model for tracking PAIA state.

### 3.10 File-Based Message Inbox Routing (MessageRouterMixin)

**What it does**: Persists messages as JSON files in per-agent inbox directories.

| Method | What It Does | Underlying Operations |
|--------|-------------|----------------------|
| `get_inbox(agent_id)` | Reads all JSON files from `{data_dir}/inboxes/{agent_id}/` | `Path.mkdir()` + `Path.glob("*.json")` + `json.loads(Path.read_text())` |
| `message_router_summary()` | Counts messages per inbox | `Path.iterdir()` + `Path.glob()` |

Sancrev's messaging is in-memory (`_message_store` dict + `collections.deque`). CAVE's is file-persisted. Different persistence models.

### 3.11 tmux kill-session (CodeAgent)

**CAVE**: `CodeAgent.kill_session()` → `subprocess.run(["tmux", "kill-session", "-t", session])`

**Sancrev**: Has `POST /stop` which sets `harness.running = False` but does NOT kill the tmux session. Has `POST /kill_agent_process` which kills claude processes but not the tmux session.

### 3.12 TUI via gum (TUIMixin, optional)

**CAVE**: `TUIMixin` checks `which gum` and if available, can run: `gum confirm`, `gum choose`, `gum input`, `gum spin`, `gum style` — all via `subprocess.run(["gum", ...])` piped through `tmux send-keys`.

**Sancrev**: Has `TerminalUI` with `tmux display-message` and `tmux display-popup` but NO gum integration.

### 3.13 Module Hot-Loading (DEAD — NOT IMPLEMENTED)

CAVE's http_server.py references `list_modules()`, `load_module()`, `unload_module()`, `get_module_history()` but these methods are NOT defined on CAVEAgent or any mixin. These endpoints would raise `AttributeError` at runtime. **This is NOT a real capability — it is dead code.**

---

## SUMMARY TABLES

### Shared Capabilities (Both Servers)

| # | Capability | Underlying Operation |
|---|-----------|---------------------|
| 1 | tmux session check | `subprocess.run(["tmux", "has-session"])` |
| 2 | tmux session create | `subprocess.run(["tmux", "new-session"])` |
| 3 | tmux send-keys | `subprocess.run(["tmux", "send-keys"])` |
| 4 | tmux capture-pane | `subprocess.run(["tmux", "capture-pane"])` |
| 5 | tmux display-message | `subprocess.run(["tmux", "display-message"])` |
| 6 | Hook enable/disable toggle | File-based JSON read/write |
| 7 | Agent registry | In-memory dict of pydantic models |
| 8 | SSE event stream | asyncio.Queue → StreamingResponse |
| 9 | CodeAgent (llegos Actor) | Same class, same inbox deque, same message types |
| 10 | FastAPI + uvicorn | Same web framework |

### Sancrev-Only Capabilities (What CAVE Truly Cannot Do)

| # | Capability | Truly New Code? | Underlying New Operations |
|---|-----------|----------------|--------------------------|
| 1 | Send-and-wait polling | YES | Poll loop + stability detection + marker extraction |
| 2 | Bash script generation + nohup background exec | YES | `subprocess.Popen(start_new_session=True)`, pgrep wait loops |
| 3 | Direct code execution | YES | `subprocess.run([python/bash, "-c", code])` |
| 4 | Process kill | YES | `ps aux | grep` + `kill -9` |
| 5 | Persona control | YES (trivial) | 3 pathlib operations on `/tmp/active_persona` |
| 6 | Domain builders (CAVE/SANCTUM/PAIA) | YES (external pkgs) | Pydantic models + JSON file CRUD |
| 7 | GEAR event system | YES | Event types + proof handler + dimension scoring |
| 8 | Message store + history + aliasing + read/unread | YES | In-memory dicts/sets + llegos method exposure |
| 9 | HTTP relay to agents | YES | `httpx.AsyncClient().post()` |
| 10 | EventRouter (structured routing) | YES | Routing dispatch + event log + hook injection files |
| 11 | OutputWatcher (conditional) | YES | 9 compiled regex patterns + event emission |
| 12 | Psyche/World/System modules (conditional) | YES | Event processing modules |
| 13 | youknow_kernel integration | YES | PIOEntity base model for PAIA |
| 14 | SSE keepalive | NO (1 line) | `asyncio.wait_for` timeout wrapper |
| 15 | CORS middleware | NO (1 line) | `app.add_middleware()` |

### CAVE-Only Capabilities (What Sancrev Gains by Extending)

| # | Capability | What Sancrev Currently Has Instead |
|---|-----------|-----------------------------------|
| 1 | Hook processing pipeline (registry + class hooks + script hooks) | Toggle flags only |
| 2 | Loop lifecycle (start/stop/pause/resume/trigger) | Nothing |
| 3 | AutoModeDNA (loop sequencing + transitions) | Nothing |
| 4 | OMNISANC zone detection + zone-based hook activation | Nothing |
| 5 | Claude state reading (full filesystem introspection) | Nothing |
| 6 | Config archiving/injection (snapshot + restore) | Nothing |
| 7 | Anatomy (Heart/Blood/Organs + SDNA heartbeat) | Conditional modules (different purpose) |
| 8 | Remote agent spawning (SDNA agent_step) | HTTP relay (different approach) |
| 9 | PAIA state management (heartbeat timestamps) | PAIABuilder (different data model) |
| 10 | File-based inbox routing (persistent) | In-memory messaging (volatile) |
| 11 | tmux kill-session | harness.running = False (no session kill) |
| 12 | TUI via gum (interactive terminal) | TerminalUI (display only, no gum) |

---

*Comparison complete. 10 shared capabilities, 15 sancrev-only capabilities (13 truly new, 2 trivial), 12 CAVE-only capabilities that sancrev gains by extending.*
