# SANCREV HTTP Server — Deep Callgraph Trace

**File**: `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/http_server.py`
**Lines**: 1843
**Date Traced**: 2026-02-16

---

## IMPORT DEPENDENCY MAP

```
http_server.py
├── stdlib: asyncio, json, logging, os, pathlib.Path, typing, contextlib.asynccontextmanager
├── external: fastapi (FastAPI, Request), fastapi.responses (StreamingResponse),
│             fastapi.middleware.cors (CORSMiddleware), pydantic (BaseModel), httpx (lazy)
├── ..core.harness → PAIAHarness, HarnessConfig
│   ├── stdlib: subprocess, time, re, tempfile, os, dataclasses, typing, pathlib.Path
│   ├── conditional: events.psyche.module (PsycheModule), events.world.module (WorldModule),
│   │                events.system.module (SystemModule) [HAS_MODULES flag]
│   ├── conditional: .output_watcher → OutputWatcher, DetectedEvent, EventType [HAS_WATCHER]
│   │   └── stdlib: re, logging, dataclasses, typing, enum
│   ├── conditional: .event_router → EventRouter, Event, EventSource, EventOutput,
│   │                InTerminalObject, TerminalObjectType, HookInjection, InjectionType [HAS_ROUTER]
│   │   └── stdlib: json, logging, dataclasses, enum, pathlib.Path, typing
│   └── conditional: .terminal_ui → TerminalUI [HAS_ROUTER]
│       └── stdlib: subprocess, logging, abc, dataclasses, enum, typing
├── ..core.hook_control → HookControl, HookType, ALL_HOOKS
│   └── stdlib: json, pathlib.Path, typing
├── ..core.persona_control → PersonaControl
│   └── stdlib: pathlib.Path
├── ..core.self_command_generator → SelfCommandGenerator, RestartConfig, CompactConfig, InjectConfig
│   └── stdlib: json, subprocess, dataclasses, pathlib.Path, typing
├── ..core.agent → CodeAgent, InboxMessage, UserPromptMessage, SystemEventMessage,
│                   BlockedMessage, CompletedMessage, IngressType,
│                   create_user_message, create_system_event
│   ├── stdlib: asyncio, logging, subprocess, time, traceback, collections.deque,
│   │           dataclasses, datetime, pathlib.Path, typing, json, os, enum
│   ├── external: pydantic (Field, PrivateAttr)
│   └── llegos → Actor, Message, Object
│       └── /tmp/sanctuary-system/llegos/src/llegos/llegos.py
│           ├── stdlib: functools, typing, collections.abc, contextvars, datetime, time
│           └── external: beartype, deepmerge, ksuid, networkx (DiGraph, MultiGraph),
│                         pydantic, pydash, pyee (EventEmitter), sorcery
├── llegos → Message
├── llegos.llegos → message_chain, message_list
├── cave_builder → CAVEBuilder
│   └── /tmp/cave-builder/cave_builder/core.py
│       ├── stdlib: json, os, pathlib.Path, typing, datetime
│       └── .models → CAVE, ValueLadder, Offer, Journey, Framework, etc. (Pydantic models)
├── sanctum_builder → SANCTUMBuilder
│   └── /tmp/sanctum-builder/sanctum_builder/core.py
│       ├── stdlib: json, os, pathlib.Path, typing, datetime, date
│       └── .models → SANCTUM, LifeDomain, RitualSpec, GoalSpec, etc. (Pydantic models)
├── paia_builder.core → PAIABuilder
│   └── /tmp/paia-builder/paia_builder/core.py
│       ├── stdlib: pathlib.Path, typing, datetime
│       ├── conditional: sanctuary_revolution.harness.events.gear_events (circular ref)
│       ├── .models → PAIA, GEAR, SkillSpec, MCPSpec, etc. (Pydantic models)
│       │   └── external: youknow_kernel (PIOEntity, ValidationLevel, YOUKNOW)
│       └── .utils (storage/GIINT helper functions)
└── ..events.gear_events → GEAREventType, GEARDimensionType, AcceptanceEvent,
                            GEARProofHandler, emit_gear_state, parse_acceptance_event
    ├── stdlib: logging, dataclasses, enum, typing, datetime
    └── ..core.event_router → Event, EventSource, EventOutput, HookInjection, etc.
```

---

## ENDPOINT CALLGRAPHS

### 1. POST /spawn (http_server.py:165)

```
spawn_agent(req: SpawnRequest)
  → get_harness() [http_server.py:79]
    → PAIAHarness() [harness.py:69]
      → HarnessConfig() [harness.py:48]
        → os.environ.get("AGENT_COMMAND", "") [stdlib]
        → os.getcwd() [stdlib]
      → PsycheModule() [conditional, HAS_MODULES]
      → WorldModule() [conditional, HAS_MODULES]
      → SystemModule() [conditional, HAS_MODULES]
      → OutputWatcher() [conditional, HAS_WATCHER] [output_watcher.py:51]
        → Compiles DEFAULT_PATTERNS (9 regex PatternMatchers) [output_watcher.py:62-140]
      → TerminalUI(session) [conditional, HAS_ROUTER] [terminal_ui.py:166]
      → EventRouter(terminal_ui) [conditional, HAS_ROUTER] [event_router.py:149]
        → Path("/tmp/paia_hooks").mkdir(parents=True, exist_ok=True) [stdlib]
    → harness.on_event(event_callback) [harness.py:318]
      → self._event_callbacks.append(callback) [list append]
  → harness.config.agent_command = req.agent_command [attribute set]
  → harness.config.working_directory = req.working_directory [attribute set]
  → harness.on_event(event_callback) [harness.py:318] (duplicate registration)
  → harness.start() [harness.py:260]
    → self.create_session() [harness.py:112]
      → self.session_exists() [harness.py:107]
        → self._run_tmux("has-session", "-t", session) [harness.py:102]
          → subprocess.run(["tmux", "has-session", "-t", "paia-agent"], capture_output=True, text=True) [stdlib]
      → self._run_tmux("new-session", "-d", "-s", session, "-c", working_dir) [harness.py:102]
        → subprocess.run(["tmux", "new-session", "-d", "-s", "paia-agent", "-c", "/home/GOD"], ...) [stdlib]
    → self.spawn_agent() [harness.py:130]
      → RuntimeError if no agent_command [harness.py:136]
      → self.session_exists() [see above]
      → self._run_tmux("send-keys", "-t", session, agent_command, "Enter") [harness.py:102]
        → subprocess.run(["tmux", "send-keys", "-t", "paia-agent", "claude", "Enter"], ...) [stdlib]
    → time.sleep(2) [stdlib]
  → return {"status": "spawned", "session": ..., "agent": ...}
```

**Terminal**: tmux new-session + tmux send-keys
**Depth**: 5 hops to stdlib

---

### 2. GET /status (http_server.py:187)

```
get_status()
  → get_harness() [http_server.py:79] (see /spawn for full PAIAHarness init)
  → harness.running [bool attribute]
  → harness.session_exists() [harness.py:107]
    → self._run_tmux("has-session", "-t", session) [harness.py:102]
      → subprocess.run(["tmux", "has-session", "-t", "paia-agent"], ...) [stdlib]
  → harness.config.tmux_session [str attribute]
  → harness.config.agent_command [str attribute]
  → return {"running": bool, "session_exists": bool, "session": str, "agent_command": str}
```

**Terminal**: tmux has-session
**Depth**: 3 hops to stdlib

---

### 3. POST /send (http_server.py:200)

```
send_to_agent(req: SendRequest)
  → get_harness() [http_server.py:79]
  → harness.session_exists() [harness.py:107]
    → subprocess.run(["tmux", "has-session", ...]) [stdlib]
  → asyncio.get_event_loop() [stdlib]
  → loop.run_in_executor(None, lambda: harness.send_and_wait(prompt, timeout)) [stdlib]
    → harness.send_and_wait(prompt, timeout) [harness.py:198]
      → harness.capture_pane() [harness.py:188]
        → self._run_tmux("capture-pane", "-t", session, "-p", "-S", "-5000") [harness.py:102]
          → subprocess.run(["tmux", "capture-pane", ...]) [stdlib]
      → harness.send_to_agent(prompt) [harness.py:181]
        → harness.send_keys([text, "Enter"]) [harness.py:154]
          → time.sleep(item) [stdlib] (if numeric)
          → subprocess.run(["tmux", "send-keys", "-t", session, item]) [stdlib]
      → POLL LOOP: time.sleep(poll_interval) + capture_pane() until stable+marker
      → Extract response from between ❯ markers
  → return {"response": str, "prompt": str}
```

**Terminal**: tmux capture-pane (repeated), tmux send-keys
**Depth**: 4 hops to stdlib

---

### 4. POST /inject (http_server.py:221)

```
inject_event(req: InjectRequest)
  → get_harness() [http_server.py:79]
  → harness.inject([formatted_message]) [harness.py:282]
    → Path("/tmp/paia_injection.txt").write_text(messages) [stdlib]
    → IF HAS_WATCHER:
      → DetectedEvent(event_type=EventType.INJECTION, ...) [output_watcher.py:33]
      → harness._emit_event(event) [harness.py:322]
        → FOR callback IN self._event_callbacks:
          → callback(event) [calls event_callback from http_server.py:139]
            → _event_queue.put_nowait({type, content, metadata}) [stdlib asyncio.Queue]
  → return {"injected": True, "domain": str, "message": str}
```

**Terminal**: File I/O to /tmp/paia_injection.txt
**Depth**: 3 hops to stdlib

---

### 5. POST /event (http_server.py:231)

```
push_event(req: GenericEventRequest)
  → datetime.now().isoformat() [stdlib]
  → _event_queue.put_nowait(event_data) [stdlib asyncio.Queue]
  → return {"success": bool, "event_type": str}
```

**Terminal**: None (pure in-memory queue)
**Depth**: 1 hop to stdlib

---

### 6. GET /events (http_server.py:261)

```
events_stream(request: Request)
  → StreamingResponse(event_generator(), media_type="text/event-stream", ...) [fastapi]
    → event_generator() [http_server.py:152]
      → LOOP:
        → asyncio.wait_for(_event_queue.get(), timeout=30.0) [stdlib]
        → json.dumps(event) [stdlib]
        → yield f"data: {json_str}\n\n"
        → ON TimeoutError: yield ": keepalive\n\n"
```

**Terminal**: None (SSE stream from asyncio.Queue)
**Depth**: 2 hops to stdlib

---

### 7. GET /capture (http_server.py:283)

```
capture_terminal()
  → get_harness() [http_server.py:79]
  → harness.capture_pane(history_limit=500) [harness.py:188]
    → self._run_tmux("capture-pane", "-t", session, "-p", "-S", "-500") [harness.py:102]
      → subprocess.run(["tmux", "capture-pane", "-t", "paia-agent", "-p", "-S", "-500"], ...) [stdlib]
  → return {"content": str, "lines": int}
```

**Terminal**: tmux capture-pane
**Depth**: 3 hops to stdlib

---

### 8. POST /stop (http_server.py:291)

```
stop_harness()
  → get_harness() [http_server.py:79]
  → harness.stop() [harness.py:310]
    → self.running = False [attribute set]
  → return {"stopped": True}
```

**Terminal**: None (just sets flag)
**Depth**: 2 hops

---

### 9. GET /hooks (http_server.py:301)

```
get_hooks()
  → HookControl.get_all() [hook_control.py:74]
    → HookControl._load() [hook_control.py:34]
      → HOOK_CONFIG = Path("/tmp/hook_config.json")
      → Path.exists() [stdlib]
      → json.loads(Path.read_text()) [stdlib]
      → OR return {h: False for h in ALL_HOOKS}
  → return dict[str, bool]
```

**Terminal**: File I/O to /tmp/hook_config.json
**Depth**: 2 hops to stdlib

---

### 10. POST /hooks/{hook_type}/enable (http_server.py:307)

```
enable_hook(hook_type: str)
  → hook_type in ALL_HOOKS [list check]
  → HookControl.enable(hook_type) [hook_control.py:46]
    → HookControl._load() → json.loads(Path("/tmp/hook_config.json").read_text()) [stdlib]
    → config[hook_type] = True
    → HookControl._save(config) → Path.write_text(json.dumps(config)) [stdlib]
  → return {"hook": str, "enabled": True}
```

**Terminal**: File I/O to /tmp/hook_config.json (read + write)
**Depth**: 2 hops to stdlib

---

### 11. POST /hooks/{hook_type}/disable (http_server.py:316)

Same pattern as enable, sets `config[hook_type] = False`.

---

### 12. POST /hooks/{hook_type}/toggle (http_server.py:325)

```
toggle_hook(hook_type: str)
  → HookControl.toggle(hook_type) [hook_control.py:60]
    → _load() → config[hook_type] = not current → _save()
    → return new_state: bool
  → return {"hook": str, "enabled": bool}
```

---

### 13. GET /persona (http_server.py:336)

```
get_persona()
  → PersonaControl.is_active() [persona_control.py:32]
    → Path("/tmp/active_persona").exists() [stdlib]
    → Path.read_text().strip() != "" [stdlib]
  → PersonaControl.get_active() [persona_control.py:24]
    → Path("/tmp/active_persona").read_text().strip() [stdlib]
  → return {"active": bool, "persona": str|None}
```

**Terminal**: File I/O to /tmp/active_persona
**Depth**: 2 hops to stdlib

---

### 14. POST /persona/{name} (http_server.py:345)

```
activate_persona(name: str)
  → PersonaControl.activate(name) [persona_control.py:14]
    → Path("/tmp/active_persona").write_text(name) [stdlib]
  → return {"persona": str, "activated": True}
```

---

### 15. DELETE /persona (http_server.py:352)

```
deactivate_persona()
  → PersonaControl.deactivate() [persona_control.py:18]
    → Path("/tmp/active_persona").unlink(missing_ok=True) [stdlib]
  → return {"deactivated": True}
```

---

### 16. POST /self/restart (http_server.py:380)

```
self_restart(req: RestartRequest)
  → RestartConfig(...) [self_command_generator.py:15]
  → SelfCommandGenerator.execute_restart(config) [self_command_generator.py:183]
    → SelfCommandGenerator.generate_restart_script(config) [self_command_generator.py:96]
      → Builds bash script string with tmux send-keys commands
    → Path("/tmp/paia_restart_handler.sh").write_text(script) [stdlib]
    → Path.chmod(0o755) [stdlib]
    → subprocess.Popen(["nohup", "/tmp/paia_restart_handler.sh"], stdout=DEVNULL, ..., start_new_session=True) [stdlib]
  → return {"scheduled": True, "config": dict}
```

**Terminal**: Writes bash script, runs nohup in background
**Generated script executes**: tmux send-keys /exit → pgrep wait loop → tmux send-keys claude → /resume → post-restart message
**Depth**: 3 hops to stdlib

---

### 17. POST /self/compact (http_server.py:393)

```
self_compact(req: CompactRequest)
  → CompactConfig(...) [self_command_generator.py:34]
  → SelfCommandGenerator.execute_compact(config) [self_command_generator.py:200]
    → SelfCommandGenerator.generate_compact_script(config) [self_command_generator.py:148]
      → Builds bash script: tmux send-keys /compact
    → subprocess.run(["bash", "-c", script], capture_output=True) [stdlib]
  → return {"success": bool, "config": dict}
```

**Terminal**: subprocess.run bash → tmux send-keys
**Depth**: 3 hops to stdlib

---

### 18. POST /self/inject (http_server.py:405)

```
self_inject(req: InjectMessageRequest)
  → InjectConfig(...) [self_command_generator.py:43]
  → SelfCommandGenerator.execute_inject(config) [self_command_generator.py:207]
    → SelfCommandGenerator.generate_inject_script(config) [self_command_generator.py:171]
      → Builds bash script: tmux send-keys message [Enter]
    → subprocess.run(["bash", "-c", script], capture_output=True) [stdlib]
  → return {"success": bool, "message": str}
```

---

### 19. POST /execute (http_server.py:425)

```
execute_code(req: ExecuteCodeRequest)
  → import subprocess, sys, datetime [stdlib]
  → IF language == "python":
    → subprocess.run([sys.executable, "-c", req.code], capture_output=True, text=True, timeout=req.timeout) [stdlib]
  → ELIF language == "bash":
    → subprocess.run(["bash", "-c", req.code], capture_output=True, text=True, timeout=req.timeout) [stdlib]
  → return {"success": bool, "stdout": str, "stderr": str, "exit_code": int, "duration_ms": int}
```

**Terminal**: Direct subprocess execution of arbitrary code
**Depth**: 1 hop to stdlib

---

### 20. POST /interrupt (http_server.py:461)

```
interrupt_claude(double: bool = False)
  → get_harness() [http_server.py:79]
  → subprocess.run(["tmux", "send-keys", "-t", session, "Escape"], check=True) [stdlib]
  → IF double:
    → asyncio.sleep(0.05) [stdlib]
    → subprocess.run(["tmux", "send-keys", "-t", session, "Escape"], check=True) [stdlib]
  → return {"sent": "Escape", "double": bool}
```

---

### 21. POST /exit (http_server.py:475)

```
exit_claude()
  → get_harness() [http_server.py:79]
  → subprocess.run(["tmux", "send-keys", "-t", session, "/exit", "Enter"], check=True) [stdlib]
  → return {"sent": "/exit"}
```

---

### 22. POST /force_exit (http_server.py:485)

```
force_exit_claude()
  → get_harness() [http_server.py:79]
  → subprocess.run(["tmux", "send-keys", "-t", session, "C-c"], check=True) [stdlib]
  → return {"sent": "C-c"}
```

---

### 23. POST /kill_agent_process (http_server.py:495)

```
kill_agent_process()
  → subprocess.run(["sh", "-c", "ps aux | grep '[c]laude' | awk '{print $2}'"], ...) [stdlib]
  → FOR pid IN pids:
    → subprocess.run(["kill", "-9", pid], capture_output=True) [stdlib]
  → return {"killed": list[str]}
```

---

### 24. POST /gear/accept (http_server.py:585)

```
accept_gear_proof(req: GEARAcceptRequest)
  → AcceptanceEvent(...) [gear_events.py:237]
    → GEAREventType(req.event_type) [gear_events.py:31, enum validation]
    → GEARDimensionType(req.dimension) [gear_events.py:47, enum validation]
  → _proof_handler.handle(event) [gear_events.py:272]
    → GEARProofHandler(paia_store=get_paia) [gear_events.py:258]
    → handler = self._handlers.get(event.event_type) [dict lookup]
    → handler(event) → one of:
      → _handle_component_accepted(event) [gear_events.py:288]
        → self.paia_store(event.paia_name) → get_paia(name) [http_server.py:545]
          → _load_paia_store() [http_server.py:529]
            → PAIA_STORE_FILE = Path("/tmp/heaven_data/paia_store.json")
            → json.loads(Path.read_text()) [stdlib]
          → paia_builder.models.PAIA.model_validate(paia_data) [pydantic]
        → paia.gear_state.gear.notes.append(note) [list append]
      → _handle_achievement_validated(event) [gear_events.py:309]
        → same paia_store lookup → paia.gear_state.achievements.notes.append()
      → _handle_reality_grounded(event) [gear_events.py:327]
        → same paia_store lookup → paia.gear_state.reality.notes.append()
      → _handle_proof_rejected(event) [gear_events.py:343]
        → same paia_store lookup → getattr(paia.gear_state, dimension.value).notes.append()
  → return {"success": bool, ...}
```

**Terminal**: File I/O to /tmp/heaven_data/paia_store.json
**Depth**: 5 hops to stdlib
**Note**: Reads but does NOT save back — proof notes are modified on in-memory PAIA but not persisted!

---

### 25. POST /gear/emit (http_server.py:611)

```
emit_gear(req: GEARStateRequest)
  → get_paia(req.paia_name) [http_server.py:545]
    → _load_paia_store() → json.loads(Path.read_text()) [stdlib]
    → PAIA.model_validate(paia_data) [pydantic]
  → get_harness() → harness.router [EventRouter instance]
  → emit_gear_state(router, paia_name, paia.gear_state) [gear_events.py:151]
    → gear_event(GEAREventType.GEAR_STATE_CHANGED, ...) [gear_events.py:59]
      → Event(source=EventSource.SYSTEM, ...) [event_router.py:107]
        → EventOutput(sse_emit=True, sse_data={...}, in_terminal=InTerminalObject(...))
    → router.route(event) [event_router.py:169]
      → self._event_log.append(event) [list]
      → _route_to_terminal(event, obj) [event_router.py:196]
        → terminal_ui.notify(InTerminalNotification(...)) [terminal_ui.py:177]
          → _show_flash_notification(n) [terminal_ui.py:184]
            → subprocess.run(["tmux", "display-message", "-t", session, ...]) [stdlib]
      → _route_to_sse(event) [event_router.py:268]
        → FOR callback IN self._sse_callbacks: callback(event)
  → return {"success": True, "emitted": str}
```

**Terminal**: tmux display-message (notification) + SSE emission
**Depth**: 6 hops to stdlib

---

### 26. GET /gear/{paia_name} (http_server.py:626)

```
get_gear_state(paia_name: str)
  → get_paia(paia_name) [http_server.py:545]
    → _load_paia_store() → json.loads(Path.read_text()) [stdlib]
    → PAIA.model_validate(paia_data) [pydantic]
  → Access paia.gear_state attributes (level, phase, total_points, overall, dimensions)
  → return dict with gear state
```

**Terminal**: File I/O to /tmp/heaven_data/paia_store.json
**Depth**: 3 hops to stdlib

---

### 27. POST /gear/register (http_server.py:649)

```
register_paia(paia_data: dict)
  → paia_builder.models.PAIA.model_validate(paia_data) [pydantic]
    → youknow_kernel.PIOEntity (base class) [youknow-kernel]
  → set_paia(paia.name, paia) [http_server.py:558]
    → _load_paia_store() [http_server.py:529]
    → store[name] = paia.model_dump(mode='json') [pydantic]
    → _save_paia_store(store) [http_server.py:539]
      → _ensure_store_dir() → Path.mkdir() [stdlib]
      → Path.write_text(json.dumps(store)) [stdlib]
  → return {"success": True, "registered": str}
```

**Terminal**: File I/O to /tmp/heaven_data/paia_store.json
**Depth**: 3 hops to stdlib

---

### 28. GET /gear/list (http_server.py:666)

```
list_registered_paias()
  → _load_paia_store() → json.loads(Path.read_text()) [stdlib]
  → return {"paias": list(store.keys()), "count": int}
```

---

### 29-32. CAVE ENDPOINTS (http_server.py:676-712)

#### GET /cave/list (http_server.py:678)
```
cave_list()
  → get_cave_builder() [http_server.py:54]
    → CAVEBuilder() [/tmp/cave-builder/cave_builder/core.py:20]
      → Path(os.environ.get("CAVE_STORAGE_DIR", ".../caves")) [stdlib]
      → Path.mkdir(parents=True, exist_ok=True) [stdlib]
  → builder.list_caves() [core.py:87]
    → self.storage_dir.glob("*.json") [stdlib]
    → FOR path: CAVE.model_validate_json(path.read_text()) [pydantic]
  → return {"items": list, "count": int}
```

#### GET /cave/status (http_server.py:685)
```
cave_status()
  → get_cave_builder()
  → builder.which() [core.py:82]
    → _get_current_name() → json.loads(Path.read_text()).get("current") [stdlib]
  → builder.status() [core.py:106]
    → _ensure_current() → _load(name) → CAVE.model_validate_json(Path.read_text()) [pydantic]
  → return dict
```

#### GET /cave/offers (http_server.py:694)
```
cave_offers()
  → get_cave_builder()
  → builder.list_offers() [core.py:201]
    → _ensure_current() → loads CAVE from JSON
    → return [{"stage": k.value, "name": v.name, "price": v.price} for k, v in cave.value_ladder.offers.items()]
```

#### GET /cave/journeys (http_server.py:704)
```
cave_journeys()
  → get_cave_builder()
  → builder.list_journeys() [core.py:236]
    → _ensure_current() → loads CAVE from JSON
    → return [{"title": j.title, "domain": j.domain.value, "published": j.published} for j in cave.journeys]
```

**Terminal**: File I/O to /tmp/heaven_data/caves/*.json
**Depth**: 3 hops to stdlib

---

### 33-36. SANCTUM ENDPOINTS (http_server.py:715-755)

#### GET /sanctum/list (http_server.py:717)
```
sanctum_list()
  → get_sanctum_builder() [http_server.py:60]
    → SANCTUMBuilder() [/tmp/sanctum-builder/sanctum_builder/core.py:28]
      → Path(os.environ.get("SANCTUM_STORAGE_DIR", ".../sanctums")) [stdlib]
  → builder.list_sanctums() [core.py:155]
    → self.storage_dir.glob("*.json") [stdlib]
    → FOR path: SANCTUM.model_validate_json(path.read_text()) [pydantic]
```

#### GET /sanctum/status (http_server.py:724)
```
sanctum_status()
  → get_sanctum_builder()
  → builder.which() [core.py:217]
    → _get_current_name() → json.loads(Path.read_text()) [stdlib]
  → builder.status() [core.py:84]
    → _ensure_current() → SANCTUM.model_validate_json(Path.read_text()) [pydantic]
    → Accesses sanctum.sanctuary_degree, mvs_name, rituals, boundaries, goals, domain_scores
```

#### GET /sanctum/rituals (http_server.py:733)
```
sanctum_rituals()
  → get_sanctum_builder()
  → builder._ensure_current() → loads SANCTUM from JSON
  → [{"name": r.name, "domain": r.domain.value, "frequency": r.frequency.value} for r in sanctum.rituals]
```

#### GET /sanctum/goals (http_server.py:745)
```
sanctum_goals()
  → same pattern → [{"name": g.name, "domain": g.domain.value, "progress": g.progress} for g in sanctum.goals]
```

**Terminal**: File I/O to /tmp/heaven_data/sanctums/*.json
**Depth**: 3 hops to stdlib

---

### 37-90+. PAIAB ENDPOINTS (http_server.py:758-1158)

All PAIAB endpoints follow the same pattern:

```
paiab_<action>(req)
  → get_paiab_builder() [http_server.py:72]
    → PAIABuilder() [/tmp/paia-builder/paia_builder/core.py:32]
      → utils.get_storage_dir(storage_dir) → Path(os.environ.get("PAIA_STORAGE_DIR", "...")) [stdlib]
  → builder.<method>(...) [core.py]
    → builder._ensure_current() [core.py:85]
      → utils.load_current_name() → json.loads(Path.read_text()) [stdlib]
      → utils.load_paia() → PAIA.model_validate_json(Path.read_text()) [pydantic]
        → youknow_kernel.PIOEntity (base model class)
    → [method-specific logic]
    → builder._save(paia) [core.py:94]
      → utils.save_paia() → Path.write_text(paia.model_dump_json()) [stdlib]
```

**Key PAIAB methods and their terminal reach:**

| Endpoint | Method | Extra Dependencies |
|----------|--------|--------------------|
| GET /paiab/list | list_paias() | File glob *.json |
| GET /paiab/status | status() | Read paia JSON |
| POST /paiab/select/{name} | select(name) | Write config JSON |
| POST /paiab/new | new(name, desc, ...) | Optional: shutil.copy, GIINT via giint-llm-intelligence MCP |
| DELETE /paiab/{name} | delete(name) | Delete paia JSON file |
| POST /paiab/fork | fork_paia() | Copy + transform + save |
| POST /paiab/tick_version | tick_version() | Modify + save |
| GET /paiab/components/{type} | list_components() | Read paia JSON |
| POST /paiab/add/skill | add_skill() | Create spec → append → log_experience → save |
| POST /paiab/add/mcp | add_mcp() | Same pattern as add_skill |
| POST /paiab/add/hook | add_hook() | Same pattern |
| POST /paiab/add/command | add_command() | Same pattern |
| POST /paiab/add/agent | add_agent() | Same pattern |
| POST /paiab/add/persona | add_persona() | Same pattern |
| POST /paiab/add/plugin | add_plugin() | Same pattern |
| POST /paiab/add/flight | add_flight() | Same pattern |
| POST /paiab/add/metastack | add_metastack() | Same pattern |
| POST /paiab/advance_tier | advance_tier() | + emit_tier_advanced → EventRouter → tmux display-message |
| POST /paiab/set_tier | set_tier() | Modify + save |
| POST /paiab/goldify | goldify() | + log_experience |
| POST /paiab/regress_golden | regress_golden() | Modify + save |
| POST /paiab/update_gear | update_gear() | + emit_dimension_update → EventRouter |
| POST /paiab/sync_gear | sync_and_emit_gear() | + emit_gear_state → EventRouter → tmux display-message |
| GET /paiab/check_win | check_win() | Optional: write CLAUDE.md to git_dir |
| POST /paiab/publish | publish() | utils.publish_paia() |

**All 30+ PAIAB set/* endpoints** follow:
```
paiab_set_<field>(req)
  → get_paiab_builder()
  → builder.set_<field>(name, content) [core.py]
    → _ensure_current() → load PAIA JSON
    → find_component(paia, type, name)
    → spec.<field> = content
    → spec.updated = datetime.now()
    → _save(paia) → write JSON
    → IF GIINT_AVAILABLE: utils.complete_task(paia.name, type, name, field, task_name)
  → return {"result": str}
```

**Terminal**: File I/O to PAIA JSON store + optional GIINT MCP calls + optional tmux notifications via EventRouter
**Depth**: 3-6 hops to stdlib

---

### 91-97. AGENT REGISTRY & RELAY (http_server.py:1161-1270)

#### POST /agents/register (http_server.py:1182)
```
register_agent(reg: AgentRegistration)
  → _agent_registry[reg.agent_id] = reg [dict set]
  → return {"registered": str, "address": str}
```
**Terminal**: None (in-memory dict)

#### DELETE /agents/{agent_id} (http_server.py:1190)
```
unregister_agent(agent_id: str)
  → del _agent_registry[agent_id] [dict delete]
```

#### GET /agents (http_server.py:1199)
```
list_agents()
  → {aid: reg.model_dump() for aid, reg in _agent_registry.items()} [pydantic]
```

#### GET /agents/{agent_id} (http_server.py:1208)
```
get_agent(agent_id: str)
  → _agent_registry[agent_id].model_dump() [pydantic]
```

#### POST /agents/{agent_id}/execute (http_server.py:1216)
```
relay_execute(agent_id: str, req: RelayExecuteRequest)
  → reg = _agent_registry[agent_id]
  → httpx.AsyncClient().post(f"{reg.address}/execute", json={...}, timeout=...) [httpx]
    → HTTP POST to remote container (e.g., http://container-name:8421/execute)
  → return resp.json()
```
**Terminal**: HTTP relay to remote container
**Depth**: 2 hops (in-memory lookup → httpx HTTP call)

#### POST /agents/{agent_id}/interrupt (http_server.py:1237)
```
relay_interrupt(agent_id: str, double: bool)
  → httpx.AsyncClient().post(f"{reg.address}/interrupt", ...) [httpx]
```

#### POST /agents/{agent_id}/inject (http_server.py:1253)
```
relay_inject(agent_id: str, message: str, press_enter: bool)
  → httpx.AsyncClient().post(f"{reg.address}/self/inject", json={...}) [httpx]
```

---

### 98-115. AGENT MESSAGING — llegos-based (http_server.py:1273-1840)

#### POST /messages/send (http_server.py:1331)
```
send_message(req: SendMessageRequest)
  → IngressType(req.ingress) [agent.py:35, enum]
  → create_user_message(content, ingress, source_id, priority) [agent.py:438]
    → UserPromptMessage(content=..., ingress=..., source_id=..., priority=...) [agent.py:63]
      → InboxMessage(Message) → llegos.Message(Object) → Pydantic BaseModel
        → Object.__init_subclass__ → namespaced_ksuid_generator [llegos.py:32]
          → Ksuid() [ksuid lib] → unique ID generation
  → msg.metadata.update(req.metadata) [dict]
  → _message_store[msg.id] = msg [dict set]
  → _message_history.append(msg.id) [list append, capped at 1000]
  → _get_agent(req.to_agent) [http_server.py:1304]
    → _agent_instances.get(agent_id) [dict lookup]
    → OR _agent_registry.get(agent_id) [dict lookup]
  → IF target_agent: target_agent.enqueue(msg) [agent.py:161]
    → len(self._inbox) >= max → emit("inbox:overflow") [pyee EventEmitter]
    → self._inbox.append(message) [collections.deque]
    → emit("inbox:enqueued") [pyee EventEmitter]
    → IF state_file: _save_inbox() → Path.write_text(json.dumps(...)) [stdlib]
  → IF to_agent == "human" AND _event_queue:
    → _event_queue.put_nowait({"type": "human_message", "data": serialized}) [asyncio.Queue]
  → return {"status": "sent", "message_id": str, "message": dict}
```
**Terminal**: In-memory deque + optional file persistence + optional SSE
**Depth**: 4 hops to stdlib (through llegos Object → ksuid → ID generation)

#### POST /messages/reply (http_server.py:1380)
```
reply_to_message(req: ReplyMessageRequest)
  → parent = _message_store.get(req.parent_message_id) [dict lookup]
  → parent.reply(content=..., priority=...) [llegos.py Message.reply():486]
    → Message.reply_to(self, **kwargs) [llegos.py:400]
      → cls.lift(message, sender=receiver, receiver=sender, parent=message) [llegos.py Object.lift():96]
        → instance.model_dump(exclude={"id"}) → deepmerge.always_merger.merge → cls(**attrs) [pydantic]
  → _message_store[reply.id] = reply [dict]
  → _message_history.append(reply.id) [list]
  → IF parent.sender: target_agent.enqueue(reply) [agent.py:161] (see above)
```

#### GET /messages/thread/{message_id} (http_server.py:1409)
```
get_message_thread(message_id: str, height: int)
  → msg = _message_store.get(message_id) [dict]
  → message_chain(msg, height) [llegos.py:490]
    → RECURSIVE: if height > 1: yield from message_chain(message.parent, height - 1)
    → yield message
  → [_serialize_message(m) for m in chain]
```

#### GET /messages/{message_id} (http_server.py:1425)
```
get_message(message_id: str)
  → _message_store.get(message_id) [dict]
  → _serialize_message(msg) [http_server.py:1316]
    → Access msg.id, msg.sender_id, msg.receiver_id, msg.parent_id, msg.content, msg.priority,
      msg.ingress, msg.created_at, msg.metadata
    → msg.sender_id → maybe(self.sender).id [sorcery.maybe → safe attribute access]
```

#### GET /messages/inbox/{agent_id} (http_server.py:1434)
```
get_inbox(agent_id: str, unread: bool|None)
  → _get_agent(agent_id) [http_server.py:1304]
  → IF agent: iterate agent._inbox (deque) with _is_message_read_by filter
  → ELSE: filter _message_history + _message_store by to_agent metadata
  → _is_message_read_by(msg_id, agent_id) [http_server.py:1830]
    → agent_id in _read_status.get(message_id, set()) [dict + set]
```

#### GET /messages/inbox/{agent_id}/count (http_server.py:1471)
```
Similar to get_inbox but returns count only.
```

#### GET /messages/inbox/{agent_id}/peek (http_server.py:1509)
```
peek_inbox(agent_id: str)
  → agent.peek() [agent.py:194]
    → sorted(self._inbox, key=lambda m: (-m.priority, m.created_at))[0]
```

#### GET /messages/inbox/{agent_id}/pop (http_server.py:1520)
```
pop_message(agent_id: str)
  → agent.dequeue() [agent.py:176]
    → sorted(self._inbox, key=lambda m: (-m.priority, m.created_at))
    → self._inbox.remove(message) [deque]
    → emit("inbox:dequeued") [pyee]
```

#### DELETE /messages/inbox/{agent_id}/{message_id} (http_server.py:1531)
```
ack_message(agent_id: str, message_id: str)
  → iterate agent._inbox, find by id, del agent._inbox[i] [deque]
```

#### GET /messages/history (http_server.py:1545)
```
get_message_history(limit: int, agent: str|None)
  → slice _message_history[-limit:]
  → filter by sender_id/receiver_id if agent specified
```

#### POST /messages/forward (http_server.py:1570)
```
forward_message(req: ForwardMessageRequest)
  → original = _message_store.get(req.message_id) [dict]
  → target_agent = _get_agent(req.to_agent) [dict]
  → original.forward_to(target_agent) [llegos.py Message.forward_to():464]
    → Message.forward(self, receiver, **kwargs) [llegos.py:422]
      → Object.lift(message, sender=receiver_of_orig, receiver=new_target, parent=message)
  → target_agent.enqueue(forwarded) if target_agent
```

#### POST /agents/instance/register (http_server.py:1605)
```
register_agent_instance(agent_id: str, agent: CodeAgent)
  → _agent_instances[agent_id] = agent [dict]
```

---

### 116-125. THREAD ALIASING (http_server.py:1622-1763)

All thread aliasing endpoints follow the pattern:
```
<action>(message_id, ...)
  → msg = _message_store.get(message_id) [dict]
  → WALK TO ROOT: while root.parent_id and root.parent_id in _message_store: root = _message_store[root.parent_id]
  → root.metadata["thread_alias"] = alias [dict set]
```
Pure in-memory operations on _message_store dict.

---

### 126-131. READ/UNREAD STATUS (http_server.py:1765-1832)

#### POST /messages/{message_id}/read (http_server.py:1767)
```
mark_message_read(message_id: str, agent_id: str)
  → _read_status[message_id] = set() if not exists
  → _read_status[message_id].add(agent_id) [set.add]
```

#### DELETE /messages/{message_id}/read (http_server.py:1786)
```
mark_message_unread(message_id: str, agent_id: str)
  → _read_status[message_id].discard(agent_id) [set.discard]
```

#### GET /messages/{message_id}/read_by (http_server.py:1802)
```
get_message_read_by(message_id: str)
  → list(_read_status.get(message_id, set())) [set → list]
```

#### GET /messages/{message_id}/is_read (http_server.py:1816)
```
check_message_read(message_id: str, agent_id: str)
  → agent_id in _read_status.get(message_id, set()) [set membership]
```

All pure in-memory dict/set operations. **No file I/O, no subprocess.**

---

## SUMMARY: EXTERNAL SYSTEMS TOUCHED

| System | Endpoints That Touch It |
|--------|------------------------|
| **tmux** (subprocess) | /spawn, /status, /send, /capture, /interrupt, /exit, /force_exit, /self/restart, /self/compact, /self/inject, /gear/emit (via EventRouter notification), /paiab/advance_tier, /paiab/sync_gear, /paiab/update_gear |
| **File: /tmp/hook_config.json** | /hooks, /hooks/*/enable, /hooks/*/disable, /hooks/*/toggle |
| **File: /tmp/active_persona** | /persona, /persona/{name}, DELETE /persona |
| **File: /tmp/paia_injection.txt** | /inject |
| **File: /tmp/paia_restart_handler.sh** | /self/restart |
| **File: /tmp/self_command_config.json** | /self/restart, /self/compact |
| **File: /tmp/heaven_data/paia_store.json** | /gear/accept, /gear/emit, /gear/{name}, /gear/register, /gear/list |
| **File: /tmp/heaven_data/caves/*.json** | /cave/* |
| **File: /tmp/heaven_data/sanctums/*.json** | /sanctum/* |
| **File: PAIA storage dir/*.json** | /paiab/* |
| **File: /tmp/paia_hooks/pending_injection.json** | EventRouter hook injection |
| **httpx** (HTTP relay) | /agents/*/execute, /agents/*/interrupt, /agents/*/inject |
| **asyncio.Queue** (SSE) | /events, /event, /inject, /messages/send (to human) |
| **subprocess** (code execution) | /execute, /kill_agent_process |
| **llegos** (Actor/Message model) | /messages/*, /agents/instance/* |
| **pydantic** (validation) | All endpoints via request models |
| **youknow_kernel** (PIOEntity) | /gear/register, /paiab/* (via PAIA model) |

## PACKAGE LOCATIONS

| Package | Path |
|---------|------|
| harness core | /tmp/sanctuary-revolution/sanctuary_revolution/harness/core/ |
| harness events | /tmp/sanctuary-revolution/sanctuary_revolution/harness/events/ |
| harness server | /tmp/sanctuary-revolution/sanctuary_revolution/harness/server/ |
| llegos | /tmp/sanctuary-system/llegos/src/llegos/ |
| cave_builder | /tmp/cave-builder/cave_builder/ |
| sanctum_builder | /tmp/sanctum-builder/sanctum_builder/ |
| paia_builder | /tmp/paia-builder/paia_builder/ |

## ENDPOINT COUNT

| Category | Count |
|----------|-------|
| Core harness | 8 (/spawn, /status, /send, /inject, /event, /events, /capture, /stop) |
| Hook control | 4 (/hooks GET, enable, disable, toggle) |
| Persona control | 3 (GET, POST, DELETE) |
| Self commands | 3 (/self/restart, /self/compact, /self/inject) |
| Code execution | 1 (/execute) |
| Claude control | 3 (/interrupt, /exit, /force_exit) |
| Kill | 1 (/kill_agent_process) |
| GEAR events | 5 (/gear/accept, /gear/emit, /gear/{name}, /gear/register, /gear/list) |
| CAVE domain | 4 (list, status, offers, journeys) |
| SANCTUM domain | 4 (list, status, rituals, goals) |
| PAIAB management | 7 (list, status, which, select, new, delete, fork, tick_version) |
| PAIAB components | 3+10 (list, get, remove + 10 add endpoints) |
| PAIAB tier/golden | 4 (advance, set, goldify, regress) |
| PAIAB GEAR | 4 (update, sync, check_win, publish) |
| PAIAB field setters | 14 (skill_md, skill_ref, skill_resource, mcp_server, mcp_tool, hook_script, command_prompt, agent_prompt, persona_frame, flight_step, metastack_field, + more) |
| Agent registry/relay | 7 (register, unregister, list, get, execute, interrupt, inject) |
| Messaging | 13 (send, reply, thread, get, inbox, count, peek, pop, ack, history, forward, instance register) |
| Thread aliasing | 6 (set alias, get alias, set priority, delete alias, list threads) |
| Read/unread | 4 (mark read, mark unread, read_by, is_read) |
| **TOTAL** | ~**100+ endpoints** |
