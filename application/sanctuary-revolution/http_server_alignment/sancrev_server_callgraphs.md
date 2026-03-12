# Sanctuary Revolution HTTP Server — Full Callgraphs

**File**: `/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/http_server.py` (1843 lines, ~73 endpoints)

**Traced from actual source code** — every file:line verified by reading the source.

---

## IMPORTS & GLOBALS

```
from ..core.harness import PAIAHarness, HarnessConfig
  → /tmp/sanctuary-revolution/sanctuary_revolution/harness/core/harness.py

from ..core.hook_control import HookControl, HookType, ALL_HOOKS
  → /tmp/sanctuary-revolution/sanctuary_revolution/harness/core/hook_control.py

from ..core.persona_control import PersonaControl
  → /tmp/sanctuary-revolution/sanctuary_revolution/harness/core/persona_control.py

from ..core.self_command_generator import SelfCommandGenerator, RestartConfig, CompactConfig, InjectConfig
  → /tmp/sanctuary-revolution/sanctuary_revolution/harness/core/self_command_generator.py

from ..core.agent import CodeAgent, InboxMessage, UserPromptMessage, SystemEventMessage, BlockedMessage, CompletedMessage, IngressType, create_user_message, create_system_event
  → /tmp/sanctuary-revolution/sanctuary_revolution/harness/core/agent.py

from llegos import Message
from llegos.llegos import message_chain, message_list
  → /tmp/sanctuary-system/llegos/ [external package]

from cave_builder import CAVEBuilder
  → /tmp/cave-builder/cave_builder/core.py

from sanctum_builder import SANCTUMBuilder
  → /tmp/sanctum-builder/sanctum_builder/core.py

from paia_builder.core import PAIABuilder
  → /tmp/paia-builder/paia_builder/core.py

from ..events.gear_events import GEAREventType, GEARDimensionType, AcceptanceEvent, GEARProofHandler, emit_gear_state, parse_acceptance_event
  → /tmp/sanctuary-revolution/sanctuary_revolution/harness/events/gear_events.py
```

### Global Instances & Helpers

```
_harness: Optional[PAIAHarness] = None          (http_server.py:46)
_event_queue: asyncio.Queue = None               (http_server.py:47)
_cave_builder: Optional[CAVEBuilder] = None      (http_server.py:50)
_sanctum_builder: Optional[SANCTUMBuilder] = None (http_server.py:51)
_paiab_builder: Optional[PAIABuilder] = None     (http_server.py:69)
_agent_registry: Dict[str, AgentRegistration] = {} (http_server.py:1179)
_agent_instances: Dict[str, CodeAgent] = {}      (http_server.py:1276)
_message_store: Dict[str, Message] = {}          (http_server.py:1279)
_message_history: List[str] = []                 (http_server.py:1280)
_read_status: Dict[str, set] = {}               (http_server.py:1283)
_proof_handler = GEARProofHandler(paia_store=get_paia) (http_server.py:566)
```

### Factory Functions

```
get_cave_builder() (http_server.py:54)
  → CAVEBuilder.__init__() (core.py:20)
    → Path(storage_dir).mkdir() [stdlib]
    → self._config_path = storage_dir / "_config.json"

get_sanctum_builder() (http_server.py:61)
  → SANCTUMBuilder.__init__() (core.py:28)
    → Path(storage_dir).mkdir() [stdlib]
    → self._config_path = storage_dir / "_config.json"

get_paiab_builder() (http_server.py:72)
  → PAIABuilder.__init__() (core.py:35)
    → utils.get_storage_dir(storage_dir) (paia_builder/utils.py)

get_harness() (http_server.py:79)
  → PAIAHarness.__init__() (harness.py:69)
    → HarnessConfig() (harness.py:49)
    → PsycheModule() / WorldModule() / SystemModule() [conditional]
    → OutputWatcher() [conditional] (output_watcher.py)
    → TerminalUI(tmux_session) [conditional] (terminal_ui.py)
    → EventRouter(terminal_ui) [conditional] (event_router.py:149)
  → harness.on_event(event_callback) (harness.py:318)
    → self._event_callbacks.append(callback)
```

---

## LIFECYCLE

### Lifespan (http_server.py:88)
```
lifespan(app)
  startup:
    → _event_queue = asyncio.Queue()
  shutdown:
    → _harness.stop() (harness.py:310)
      → self.running = False
```

---

## CORE AGENT ENDPOINTS

### POST /spawn (http_server.py:165)
```
spawn_agent(req: SpawnRequest)
  → get_harness() (http_server.py:79)
    → PAIAHarness() [see above]
  → harness.config.agent_command = req.agent_command
  → harness.config.working_directory = req.working_directory
  → harness.on_event(event_callback) (harness.py:318)
    → self._event_callbacks.append(callback)
  → harness.start() (harness.py:260)
    → self.running = True
    → self.create_session() (harness.py:112)
      → self.session_exists() (harness.py:107)
        → self._run_tmux("has-session", "-t", session) (harness.py:102)
          → subprocess.run(["tmux", "has-session", "-t", session]) [stdlib]
      → if not exists:
        → self._run_tmux("new-session", "-d", "-s", session, "-c", working_dir) (harness.py:117)
          → subprocess.run(["tmux", "new-session", "-d", "-s", ...]) [stdlib]
    → self.spawn_agent() (harness.py:130)
      → self._run_tmux("send-keys", "-t", session, agent_command, "Enter") (harness.py:146)
        → subprocess.run(["tmux", "send-keys", "-t", ...]) [stdlib]
    → time.sleep(2) [stdlib]
```

### GET /status (http_server.py:187)
```
get_status()
  → get_harness() (http_server.py:79)
  → harness.running [attr access]
  → harness.session_exists() (harness.py:107)
    → self._run_tmux("has-session", "-t", session) (harness.py:102)
      → subprocess.run(["tmux", "has-session", "-t", session]) [stdlib]
  → harness.config.tmux_session [attr access]
  → harness.config.agent_command [attr access]
```

### POST /send (http_server.py:200)
```
send_to_agent(req: SendRequest)
  → get_harness() (http_server.py:79)
  → harness.session_exists() (harness.py:107)
    → self._run_tmux("has-session", ...) (harness.py:102)
      → subprocess.run(["tmux", ...]) [stdlib]
  → if not exists: return error
  → asyncio.get_event_loop() [stdlib]
  → loop.run_in_executor(None, lambda: harness.send_and_wait(prompt, timeout))
    → harness.send_and_wait(prompt, timeout) (harness.py:198)
      → self.capture_pane() (harness.py:188)
        → self._run_tmux("capture-pane", "-t", session, "-p", "-S", limit) (harness.py:190)
          → subprocess.run(["tmux", "capture-pane", ...]) [stdlib]
      → self.send_to_agent(prompt) (harness.py:181)
        → self.send_keys([text, "Enter"]) (harness.py:154)
          → self._run_tmux("send-keys", "-t", session, text) (harness.py:172)
            → subprocess.run(["tmux", "send-keys", ...]) [stdlib]
          → self._run_tmux("send-keys", "-t", session, "Enter")
      → [polling loop]:
        → time.sleep(poll_interval) [stdlib]
        → self.capture_pane() (harness.py:188) [repeated]
        → check stable_count >= 3 and response_marker in content
      → self.capture_pane() [final capture] (harness.py:188)
      → [parse response between markers]
```

### POST /inject (http_server.py:221)
```
inject_event(req: InjectRequest)
  → get_harness() (http_server.py:79)
  → harness.inject([f"[{domain}]: {message}"]) (harness.py:282)
    → Path("/tmp/paia_injection.txt").write_text(joined_messages) [stdlib]
    → if HAS_WATCHER:
      → for msg in messages:
        → DetectedEvent(event_type=EventType.INJECTION, ...) (output_watcher.py)
        → self._emit_event(event) (harness.py:322)
          → for callback in self._event_callbacks:
            → callback(event) [registered callbacks, e.g. event_callback]
```

### POST /event (http_server.py:231)
```
push_event(req: GenericEventRequest)
  → from datetime import datetime [stdlib]
  → datetime.now().isoformat() [stdlib]
  → _event_queue.put_nowait(event_data) [asyncio.Queue]
    → if QueueFull: pass
```

### GET /events (http_server.py:261)
```
events_stream(request: Request)
  → StreamingResponse(event_generator(), media_type="text/event-stream")
    → event_generator() (http_server.py:152)
      → [infinite loop]:
        → asyncio.wait_for(_event_queue.get(), timeout=30.0) [stdlib]
        → yield f"data: {json.dumps(event)}\n\n"
        → on TimeoutError: yield keepalive
```

### GET /capture (http_server.py:283)
```
capture_terminal()
  → get_harness() (http_server.py:79)
  → harness.capture_pane(history_limit=500) (harness.py:188)
    → self._run_tmux("capture-pane", "-t", session, "-p", "-S", "-500") (harness.py:190)
      → subprocess.run(["tmux", "capture-pane", ...]) [stdlib]
```

### POST /stop (http_server.py:291)
```
stop_harness()
  → get_harness() (http_server.py:79)
  → harness.stop() (harness.py:310)
    → self.running = False
```

---

## HOOK CONTROL ENDPOINTS

### GET /hooks (http_server.py:301)
```
get_hooks()
  → HookControl.get_all() (hook_control.py:74)
    → HookControl._load() (hook_control.py:34)
      → HOOK_CONFIG.exists() → Path("/tmp/hook_config.json").exists() [stdlib]
      → if exists: json.loads(HOOK_CONFIG.read_text()) [stdlib]
      → else: {h: False for h in ALL_HOOKS}
```

### POST /hooks/{hook_type}/enable (http_server.py:307)
```
enable_hook(hook_type: str)
  → if hook_type not in ALL_HOOKS: return error
  → HookControl.enable(hook_type) (hook_control.py:46)
    → HookControl._load() (hook_control.py:34)
      → Path("/tmp/hook_config.json") read [stdlib]
    → config[hook_type] = True
    → HookControl._save(config) (hook_control.py:41)
      → HOOK_CONFIG.write_text(json.dumps(config)) [stdlib]
```

### POST /hooks/{hook_type}/disable (http_server.py:316)
```
disable_hook(hook_type: str)
  → if hook_type not in ALL_HOOKS: return error
  → HookControl.disable(hook_type) (hook_control.py:52)
    → HookControl._load() (hook_control.py:34)
      → Path("/tmp/hook_config.json") read [stdlib]
    → config[hook_type] = False
    → HookControl._save(config) (hook_control.py:41)
      → HOOK_CONFIG.write_text(json.dumps(config)) [stdlib]
```

### POST /hooks/{hook_type}/toggle (http_server.py:325)
```
toggle_hook(hook_type: str)
  → if hook_type not in ALL_HOOKS: return error
  → HookControl.toggle(hook_type) (hook_control.py:60)
    → HookControl._load() (hook_control.py:34)
      → Path("/tmp/hook_config.json") read [stdlib]
    → config[hook_type] = not config.get(hook_type, False)
    → HookControl._save(config) (hook_control.py:41)
      → HOOK_CONFIG.write_text(json.dumps(config)) [stdlib]
    → return config[hook_type]
```

---

## PERSONA CONTROL ENDPOINTS

### GET /persona (http_server.py:336)
```
get_persona()
  → PersonaControl.is_active() (persona_control.py:32)
    → PERSONA_FLAG.exists() → Path("/tmp/active_persona").exists() [stdlib]
    → PERSONA_FLAG.read_text().strip() != "" [stdlib]
  → PersonaControl.get_active() (persona_control.py:24)
    → if PERSONA_FLAG.exists():
      → PERSONA_FLAG.read_text().strip() [stdlib]
    → else: return None
```

### POST /persona/{name} (http_server.py:345)
```
activate_persona(name: str)
  → PersonaControl.activate(name) (persona_control.py:14)
    → PERSONA_FLAG.write_text(name) → Path("/tmp/active_persona").write_text(name) [stdlib]
```

### DELETE /persona (http_server.py:352)
```
deactivate_persona()
  → PersonaControl.deactivate() (persona_control.py:18)
    → PERSONA_FLAG.unlink(missing_ok=True) → Path("/tmp/active_persona").unlink() [stdlib]
```

---

## SELF COMMAND ENDPOINTS

### POST /self/restart (http_server.py:380)
```
self_restart(req: RestartRequest)
  → RestartConfig(tmux_session=..., autopoiesis=..., ...) (self_command_generator.py:15)
  → SelfCommandGenerator.execute_restart(config) (self_command_generator.py:183)
    → SelfCommandGenerator.generate_restart_script(config) (self_command_generator.py:96)
      → [builds bash script string with tmux commands]
      → if config.resume_enabled: [appends /resume steps]
      → if config.autopoiesis: [appends autopoiesis message]
      → else: [appends post_restart_message]
    → Path("/tmp/paia_restart_handler.sh").write_text(script) [stdlib]
    → Path.chmod(0o755) [stdlib]
    → subprocess.Popen(["nohup", "/tmp/paia_restart_handler.sh"], start_new_session=True) [stdlib]
```

### POST /self/compact (http_server.py:393)
```
self_compact(req: CompactRequest)
  → CompactConfig(tmux_session=..., ...) (self_command_generator.py:34)
  → SelfCommandGenerator.execute_compact(config) (self_command_generator.py:200)
    → SelfCommandGenerator.generate_compact_script(config) (self_command_generator.py:148)
      → [builds bash script with tmux compact commands]
    → subprocess.run(["bash", "-c", script]) [stdlib]
    → return result.returncode == 0
```

### POST /self/inject (http_server.py:405)
```
self_inject(req: InjectMessageRequest)
  → InjectConfig(tmux_session=..., message=..., press_enter=...) (self_command_generator.py:43)
  → SelfCommandGenerator.execute_inject(config) (self_command_generator.py:207)
    → SelfCommandGenerator.generate_inject_script(config) (self_command_generator.py:171)
      → [builds bash script: tmux send-keys message]
      → if press_enter: [appends Enter send]
    → subprocess.run(["bash", "-c", script]) [stdlib]
    → return result.returncode == 0
```

---

## CODE EXECUTION ENDPOINT

### POST /execute (http_server.py:425)
```
execute_code(req: ExecuteCodeRequest)
  → import subprocess, sys [stdlib]
  → from datetime import datetime [stdlib]
  → datetime.now() [stdlib]
  → if req.language == "python":
    → subprocess.run([sys.executable, "-c", req.code], capture_output=True, text=True, timeout=req.timeout) [stdlib]
  → elif req.language == "bash":
    → subprocess.run(["bash", "-c", req.code], capture_output=True, text=True, timeout=req.timeout) [stdlib]
  → else: return error "Unsupported language"
  → on TimeoutExpired: return error
```

---

## CLAUDE CONTROL ENDPOINTS

### POST /interrupt (http_server.py:461)
```
interrupt_claude(double: bool = False)
  → import subprocess [stdlib]
  → get_harness() (http_server.py:79)
  → session = harness.config.tmux_session
  → subprocess.run(["tmux", "send-keys", "-t", session, "Escape"], check=True) [stdlib]
  → if double:
    → asyncio.sleep(0.05) [stdlib]
    → subprocess.run(["tmux", "send-keys", "-t", session, "Escape"], check=True) [stdlib]
```

### POST /exit (http_server.py:475)
```
exit_claude()
  → import subprocess [stdlib]
  → get_harness() (http_server.py:79)
  → session = harness.config.tmux_session
  → subprocess.run(["tmux", "send-keys", "-t", session, "/exit", "Enter"], check=True) [stdlib]
```

### POST /force_exit (http_server.py:485)
```
force_exit_claude()
  → import subprocess [stdlib]
  → get_harness() (http_server.py:79)
  → session = harness.config.tmux_session
  → subprocess.run(["tmux", "send-keys", "-t", session, "C-c"], check=True) [stdlib]
```

### POST /kill_agent_process (http_server.py:495)
```
kill_agent_process()
  → import subprocess [stdlib]
  → subprocess.run(["sh", "-c", "ps aux | grep '[c]laude' | awk '{print $2}'"], capture_output=True, text=True) [stdlib]
  → [parse PIDs from stdout]
  → if no pids: return "No claude process found"
  → for pid in pids:
    → subprocess.run(["kill", "-9", pid], capture_output=True) [stdlib]
```

---

## GEAR EVENTS ENDPOINTS

### POST /gear/accept (http_server.py:585)
```
accept_gear_proof(req: GEARAcceptRequest)
  → AcceptanceEvent(event_type=GEAREventType(req.event_type), ...) (gear_events.py:237)
  → _proof_handler.handle(event) (gear_events.py:272)
    → handler = self._handlers.get(event.event_type) (gear_events.py:277)
    → handler(event) — dispatches to one of:

    [if COMPONENT_ACCEPTED]:
      → _handle_component_accepted(event) (gear_events.py:288)
        → self.paia_store(event.paia_name) → get_paia(name) (http_server.py:545)
          → _load_paia_store() (http_server.py:529)
            → PAIA_STORE_FILE.exists() [stdlib]
            → json.loads(PAIA_STORE_FILE.read_text()) [stdlib]
          → store.get(name)
          → from paia_builder.models import PAIA
          → PAIA.model_validate(paia_data) [pydantic]
        → if event.accepted:
          → paia.gear_state.gear.notes.append(note)

    [if ACHIEVEMENT_VALIDATED]:
      → _handle_achievement_validated(event) (gear_events.py:309)
        → self.paia_store(event.paia_name) → get_paia(name)
        → paia.gear_state.achievements.notes.append(note)

    [if REALITY_GROUNDED]:
      → _handle_reality_grounded(event) (gear_events.py:327)
        → self.paia_store(event.paia_name) → get_paia(name)
        → paia.gear_state.reality.notes.append(note)

    [if PROOF_REJECTED]:
      → _handle_proof_rejected(event) (gear_events.py:343)
        → self.paia_store(event.paia_name) → get_paia(name)
        → if dimension:
          → getattr(paia.gear_state, dimension.value)
          → dim_obj.notes.append(note)
```

### POST /gear/emit (http_server.py:611)
```
emit_gear(req: GEARStateRequest)
  → get_paia(req.paia_name) (http_server.py:545)
    → _load_paia_store() (http_server.py:529)
    → PAIA.model_validate(paia_data)
  → if not paia: return error
  → get_harness() (http_server.py:79)
  → emit_gear_state(harness.router, paia_name, paia.gear_state) (gear_events.py:151)
    → gear_event(event_type=GEAR_STATE_CHANGED, ...) (gear_events.py:59)
      → EventOutput(sse_emit=True) (event_router.py:81)
      → InTerminalObject(object_type=NOTIFICATION, ...) (event_router.py:56)
      → Event(source=SYSTEM, ...) (event_router.py:107)
    → router.route(event) (event_router.py:169)
      → self._event_log.append(event)
      → if output.in_terminal and self.terminal_ui:
        → self._route_to_terminal(event, obj) (event_router.py:196)
          → InTerminalNotification(...) (terminal_ui.py)
          → self.terminal_ui.notify(notification)
      → if output.hook_injection:
        → self._route_to_hook(event, injection) (event_router.py:234)
          → Path("/tmp/paia_hooks/pending_injection.json") read/write [stdlib]
      → if output.sse_emit:
        → self._route_to_sse(event) (event_router.py:268)
          → for callback in self._sse_callbacks:
            → callback(event)
```

### GET /gear/{paia_name} (http_server.py:626)
```
get_gear_state(paia_name: str)
  → get_paia(paia_name) (http_server.py:545)
    → _load_paia_store() (http_server.py:529)
    → PAIA.model_validate(paia_data)
  → if not paia: return error
  → gs = paia.gear_state [attr access]
  → gs.level, gs.phase.value, gs.total_points, gs.overall [attr access]
  → gs.gear.score, gs.gear.notes[-5:] [attr access]
  → gs.experience.score, gs.experience.notes[-5:] [attr access]
  → gs.achievements.score, gs.achievements.notes[-5:] [attr access]
  → gs.reality.score, gs.reality.notes[-5:] [attr access]
```

### POST /gear/register (http_server.py:649)
```
register_paia(paia_data: dict)
  → from paia_builder.models import PAIA
  → PAIA.model_validate(paia_data) [pydantic]
  → set_paia(paia.name, paia) (http_server.py:558)
    → _load_paia_store() (http_server.py:529)
    → store[name] = paia.model_dump(mode='json') [pydantic]
    → _save_paia_store(store) (http_server.py:539)
      → _ensure_store_dir() (http_server.py:524)
        → HEAVEN_DATA_DIR.mkdir(parents=True, exist_ok=True) [stdlib]
      → PAIA_STORE_FILE.write_text(json.dumps(store)) [stdlib]
```

### GET /gear/list (http_server.py:666)
```
list_registered_paias()
  → _load_paia_store() (http_server.py:529)
    → PAIA_STORE_FILE.exists() [stdlib]
    → json.loads(PAIA_STORE_FILE.read_text()) [stdlib]
  → list(store.keys())
```

---

## CAVE ENDPOINTS

### GET /cave/list (http_server.py:678)
```
cave_list()
  → get_cave_builder() (http_server.py:54)
  → builder.list_caves() (cave_builder/core.py:87)
    → self.storage_dir.glob("*.json") [stdlib]
    → for path: skip "_" prefixed
      → CAVE.model_validate_json(path.read_text()) [pydantic]
      → {name, mrr, journeys count, frameworks count, is_complete}
```

### GET /cave/status (http_server.py:685)
```
cave_status()
  → get_cave_builder() (http_server.py:54)
  → builder.which() (cave_builder/core.py:82)
    → self._get_current_name() (cave_builder/core.py:41)
      → self._config_path.exists() [stdlib]
      → json.loads(self._config_path.read_text()).get("current") [stdlib]
    → return name or "No CAVE selected"
  → if current == "No CAVE selected": return inactive
  → builder.status() (cave_builder/core.py:106)
    → self._ensure_current() (cave_builder/core.py:49)
      → self._get_current_name() (cave_builder/core.py:41)
      → self._load(name) (cave_builder/core.py:35)
        → CAVE.model_validate_json(path.read_text()) [pydantic]
    → [builds status string from cave fields]
```

### GET /cave/offers (http_server.py:694)
```
cave_offers()
  → get_cave_builder() (http_server.py:54)
  → builder.list_offers() (cave_builder/core.py:201)
    → self._ensure_current() (cave_builder/core.py:49)
      → self._get_current_name() → self._load(name) [file I/O]
    → cave.value_ladder.offers.items() [attr access]
    → [builds list of {stage, name, price}]
  → on ValueError: return empty + error
```

### GET /cave/journeys (http_server.py:704)
```
cave_journeys()
  → get_cave_builder() (http_server.py:54)
  → builder.list_journeys() (cave_builder/core.py:236)
    → self._ensure_current() (cave_builder/core.py:49)
    → [builds list of {title, domain, published}]
  → on ValueError: return empty + error
```

---

## SANCTUM ENDPOINTS

### GET /sanctum/list (http_server.py:717)
```
sanctum_list()
  → get_sanctum_builder() (http_server.py:61)
  → builder.list_sanctums() (sanctum_builder/core.py:155)
    → self.storage_dir.glob("*.json") [stdlib]
    → for path: skip "_" prefixed
      → SANCTUM.model_validate_json(path.read_text()) [pydantic]
      → {name, overall}
```

### GET /sanctum/status (http_server.py:724)
```
sanctum_status()
  → get_sanctum_builder() (http_server.py:61)
  → builder.which() (sanctum_builder/core.py:217)
    → self._get_current_name() (sanctum_builder/core.py:49)
      → self._config_path.exists() [stdlib]
      → json.loads(self._config_path.read_text()).get("current") [stdlib]
    → if not name: return "[HIEL] No SANCTUM selected"
    → return f"[SANCTUM] Current: {name}"
  → if "[HIEL]" in current: return inactive
  → builder.status() (sanctum_builder/core.py:84)
    → self._ensure_current() (sanctum_builder/core.py:57)
      → self._get_current_name()
      → self._load(name) (sanctum_builder/core.py:43)
        → SANCTUM.model_validate_json(path.read_text()) [pydantic]
    → [builds SOSEEH-themed status string]
```

### GET /sanctum/rituals (http_server.py:733)
```
sanctum_rituals()
  → get_sanctum_builder() (http_server.py:61)
  → builder._ensure_current() (sanctum_builder/core.py:57)
    → self._get_current_name() → self._load(name) [file I/O]
  → sanctum.rituals [attr access]
  → [{name, domain.value, frequency.value} for r in rituals]
  → on ValueError: return empty + error
```

### GET /sanctum/goals (http_server.py:745)
```
sanctum_goals()
  → get_sanctum_builder() (http_server.py:61)
  → builder._ensure_current() (sanctum_builder/core.py:57)
    → self._get_current_name() → self._load(name) [file I/O]
  → sanctum.goals [attr access]
  → [{name, domain.value, progress} for g in goals]
  → on ValueError: return empty + error
```

---

## PAIAB MANAGEMENT ENDPOINTS

### GET /paiab/list (http_server.py:906)
```
paiab_list()
  → get_paiab_builder() (http_server.py:72)
  → builder.list_paias() (paia_builder/core.py:125)
    → utils.list_all_paias(self.storage_dir) (paia_builder/utils.py)
```

### GET /paiab/status (http_server.py:912)
```
paiab_status()
  → get_paiab_builder() (http_server.py:72)
  → builder.status() (paia_builder/core.py:467)
    → self._ensure_current() (paia_builder/core.py:85)
      → utils.load_current_name(self.storage_dir)
      → utils.load_paia(self.storage_dir, name)
    → gs = paia.gear_state
    → [builds SOSEEH status: pilot/vehicle/mission_control/loops + gs.display()]
  → builder.which() (paia_builder/core.py:76)
    → utils.load_current_name(self.storage_dir)
    → utils.load_paia(self.storage_dir, name)
  → on ValueError: return inactive
```

### GET /paiab/which (http_server.py:922)
```
paiab_which()
  → get_paiab_builder() (http_server.py:72)
  → builder.which() (paia_builder/core.py:76)
    → utils.load_current_name(self.storage_dir)
    → utils.load_paia(self.storage_dir, name)
```

### POST /paiab/select/{name} (http_server.py:927)
```
paiab_select(name: str)
  → get_paiab_builder() (http_server.py:72)
  → builder.select(name) (paia_builder/core.py:70)
    → utils.get_paia_path(self.storage_dir, name).exists()
    → utils.save_current_name(self.storage_dir, name)
```

### POST /paiab/new (http_server.py:933)
```
paiab_new(req: NewPAIARequest)
  → get_paiab_builder() (http_server.py:72)
  → builder.new(name, description, git_dir, source_dir, init_giint) (paia_builder/core.py:106)
    → utils.get_paia_path(self.storage_dir, name).exists()
    → utils.create_paia(name, description, git_dir, source_dir)
    → self._save(paia) (paia_builder/core.py:94)
      → utils.save_paia(self.storage_dir, paia)
    → utils.save_current_name(self.storage_dir, name)
    → if git_dir:
      → Path(git_dir).mkdir() [stdlib]
      → utils.init_project_structure(Path(git_dir), name, description)
      → shutil.copy(paia_path, git_dir / "paia.json") [stdlib]
      → if init_giint and utils.GIINT_AVAILABLE:
        → utils.init_giint_project(name, git_dir)
```

### DELETE /paiab/{name} (http_server.py:939)
```
paiab_delete(name: str)
  → get_paiab_builder() (http_server.py:72)
  → builder.delete(name) (paia_builder/core.py:128)
    → utils.delete_paia(self.storage_dir, name)
    → if current == name: utils.get_config_path(self.storage_dir).unlink()
```

### POST /paiab/fork (http_server.py:945)
```
paiab_fork(req: ForkPAIARequest)
  → get_paiab_builder() (http_server.py:72)
  → builder.fork_paia(source_name, new_name, fork_type, description, git_dir, init_giint) (paia_builder/core.py:135)
    → utils.load_paia(self.storage_dir, source_name)
    → utils.fork_paia(source, new_name, fork_type, description, git_dir)
    → self._save(forked)
    → utils.save_current_name(self.storage_dir, new_name)
    → if git_dir:
      → Path(git_dir).mkdir() [stdlib]
      → utils.init_project_structure(...)
      → if init_giint: utils.init_giint_project(...)
```

### POST /paiab/tick_version (http_server.py:951)
```
paiab_tick_version(req: TickVersionRequest)
  → get_paiab_builder() (http_server.py:72)
  → builder.tick_version(new_version, new_description) (paia_builder/core.py:154)
    → self._ensure_current()
    → paia.version_history.append(VersionEntry(...))
    → paia.version = new_version
    → self._save(paia)
```

---

## PAIAB COMPONENT ENDPOINTS

### GET /paiab/components/{comp_type} (http_server.py:960)
```
paiab_list_components(comp_type: str)
  → get_paiab_builder() (http_server.py:72)
  → builder.list_components(comp_type) (paia_builder/core.py:165)
    → self._ensure_current()
    → getattr(paia, comp_type, [])
    → [{name, tier.value, golden.value, points, description[:50]}]
  → on ValueError: return empty + error
```

### GET /paiab/component/{comp_type}/{name} (http_server.py:969)
```
paiab_get_component(comp_type: str, name: str)
  → get_paiab_builder() (http_server.py:72)
  → builder.get_component(comp_type, name) (paia_builder/core.py:170)
    → utils.find_component(self._ensure_current(), comp_type, name)
    → {name, description, tier.value, golden.value, points, notes}
```

### DELETE /paiab/component/{comp_type}/{name} (http_server.py:974)
```
paiab_remove_component(comp_type: str, name: str)
  → get_paiab_builder() (http_server.py:72)
  → builder.remove_component(comp_type, name) (paia_builder/core.py:177)
    → self._ensure_current()
    → getattr(paia, comp_type, [])
    → for i, c in enumerate(comps): if c.name == name: comps.pop(i)
    → self._save(paia)
```

---

## PAIAB ADD COMPONENT ENDPOINTS

All follow the same pattern:
```
get_paiab_builder() → builder.add_X() → self._ensure_current() → utils.create_X_spec() → paia.Xs.append(spec) → self._after_add() → self._save(paia)
```

### POST /paiab/add/skill (http_server.py:983)
```
paiab_add_skill(req: AddSkillRequest)
  → builder.add_skill(name, domain, category, description) (paia_builder/core.py:222)
    → self._ensure_current()
    → utils.create_skill_spec(name, domain, category, description)
    → paia.skills.append(spec)
    → self._after_add(paia, "skills", name, spec) (paia_builder/core.py:187)
      → utils.log_experience(paia, COMPONENT_ADDED, ...)
      → if paia.git_dir:
        → utils.update_construction_docs(paia, comp_type, name)
        → if GIINT_AVAILABLE:
          → utils.add_component(paia.name, comp_type, name)
          → utils.add_skill_deliverables(paia.name, name)
          → utils.attach_spec_to_component(...)
    → self._save(paia)
```

### POST /paiab/add/mcp (http_server.py:989)
```
paiab_add_mcp(req: AddMCPRequest)
  → builder.add_mcp(name, description) (paia_builder/core.py:230)
    → [same pattern as add_skill with utils.create_mcp_spec]
```

### POST /paiab/add/hook (http_server.py:995)
```
paiab_add_hook(req: AddHookRequest)
  → builder.add_hook(name, hook_type, description) (paia_builder/core.py:238)
    → [same pattern with utils.create_hook_spec]
```

### POST /paiab/add/command (http_server.py:1001)
```
paiab_add_command(req: AddCommandRequest)
  → builder.add_command(name, description, argument_hint) (paia_builder/core.py:246)
    → [same pattern with utils.create_command_spec]
```

### POST /paiab/add/agent (http_server.py:1007)
```
paiab_add_agent(req: AddAgentRequest)
  → builder.add_agent(name, description) (paia_builder/core.py:254)
    → [same pattern with utils.create_agent_spec]
```

### POST /paiab/add/persona (http_server.py:1013)
```
paiab_add_persona(req: AddPersonaRequest)
  → builder.add_persona(name, domain, description, frame) (paia_builder/core.py:270)
    → [same pattern with utils.create_persona_spec]
```

### POST /paiab/add/plugin (http_server.py:1019)
```
paiab_add_plugin(req: AddPluginRequest)
  → builder.add_plugin(name, description, git_url) (paia_builder/core.py:278)
    → [same pattern with utils.create_plugin_spec]
```

### POST /paiab/add/flight (http_server.py:1025)
```
paiab_add_flight(req: AddFlightRequest)
  → builder.add_flight(name, domain, description) (paia_builder/core.py:286)
    → [same pattern with utils.create_flight_spec]
```

### POST /paiab/add/metastack (http_server.py:1031)
```
paiab_add_metastack(req: AddMetastackRequest)
  → builder.add_metastack(name, domain, description) (paia_builder/core.py:294)
    → [same pattern with utils.create_metastack_spec]
```

---

## PAIAB TIER/GOLDEN ENDPOINTS

### POST /paiab/advance_tier (http_server.py:1040)
```
paiab_advance_tier(req: AdvanceTierRequest)
  → get_paiab_builder() (http_server.py:72)
  → builder.advance_tier(comp_type, name, fulfillment) (paia_builder/core.py:381)
    → self._ensure_current()
    → utils.find_component(paia, comp_type, name)
    → old_tier = comp.tier.value
    → old_level = paia.gear_state.level
    → utils.advance_component_tier(comp, fulfillment)
    → if success:
      → utils.log_experience(paia, TIER_ADVANCED, ...)
      → self._save(paia)
      → self._emit_tier_advanced(paia, comp_type, name, old_tier, new_tier) (paia_builder/core.py:64)
        → if router and GEAR_EVENTS_AVAILABLE:
          → emit_tier_advanced(router, paia.name, ...) (gear_events.py:211)
            → gear_event(...) → Event
            → router.route(event) (event_router.py:169)
      → if level changed:
        → self._emit_level_up(paia, old_level, new_level) (paia_builder/core.py:59)
          → emit_level_up(router, ...) (gear_events.py:198)
      → if git_dir:
        → utils.update_construction_docs(paia, comp_type, name)
        → if GIINT_AVAILABLE: utils.update_giint_task_done(...)
```

### POST /paiab/set_tier (http_server.py:1046)
```
paiab_set_tier(req: SetTierRequest)
  → builder.set_tier(comp_type, name, tier, note) (paia_builder/core.py:411)
    → self._ensure_current()
    → utils.find_component(paia, comp_type, name)
    → utils.set_component_tier(comp, AchievementTier(tier), note)
    → self._save(paia)
```

### POST /paiab/goldify (http_server.py:1052)
```
paiab_goldify(req: GoldifyRequest)
  → builder.goldify(comp_type, name, note) (paia_builder/core.py:420)
    → self._ensure_current()
    → utils.find_component(paia, comp_type, name)
    → utils.advance_golden(comp, note)
    → if success:
      → utils.log_experience(paia, GOLDEN_ADVANCED, ...)
      → self._save(paia)
      → if git_dir: utils.update_construction_docs(...)
```

### POST /paiab/regress_golden (http_server.py:1058)
```
paiab_regress_golden(req: RegressGoldenRequest)
  → builder.regress_golden(comp_type, name, reason) (paia_builder/core.py:442)
    → self._ensure_current()
    → utils.find_component(paia, comp_type, name)
    → utils.regress_golden(comp, reason)
    → if success: self._save(paia)
```

---

## PAIAB GEAR ENDPOINTS

### POST /paiab/update_gear (http_server.py:1067)
```
paiab_update_gear(req: UpdateGEARRequest)
  → builder.update_gear(dimension, score, note) (paia_builder/core.py:453)
    → self._ensure_current()
    → dim = getattr(paia.gear_state, dimension)
    → old_score = dim.score
    → old_level = paia.gear_state.level
    → utils.update_gear_dimension(paia, dimension, score, note)
    → self._save(paia)
    → self._emit_dimension_update(paia, dimension, old_score, score, note) (paia_builder/core.py:52)
      → emit_dimension_update(router, ...) (gear_events.py:177)
        → gear_event(...) → Event
        → router.route(event)
    → if level changed:
      → self._emit_level_up(paia, old_level, new_level)
```

### POST /paiab/sync_gear (http_server.py:1073)
```
paiab_sync_gear()
  → builder.sync_and_emit_gear() (paia_builder/core.py:478)
    → self._ensure_current()
    → utils.sync_gear(paia)
    → self._save(paia)
    → self._emit_gear_state(paia)
      → emit_gear_state(router, paia.name, paia.gear_state) (gear_events.py:151)
        → gear_event(...) → Event
        → router.route(event)
```

### GET /paiab/check_win (http_server.py:1079)
```
paiab_check_win()
  → builder.check_win() (paia_builder/core.py:716)
    → self._ensure_current()
    → paia.gear_state.is_constructed [attr access]
    → if constructed and git_dir:
      → (Path(git_dir) / "CLAUDE.md").write_text(utils.generate_claude_md(paia)) [stdlib]
      → utils.update_gear_status_doc(paia)
```

### POST /paiab/publish (http_server.py:1085)
```
paiab_publish()
  → builder.publish() (paia_builder/core.py:724)
    → utils.publish_paia(self._ensure_current())
```

---

## PAIAB FIELD SETTER ENDPOINTS

All follow pattern:
```
get_paiab_builder() → builder.set_X() → self._ensure_current() → utils.find_component() → update field → self._save(paia) → if GIINT: utils.complete_task()
```

### POST /paiab/set/skill_md (http_server.py:1094)
```
paiab_set_skill_md(req)
  → builder.set_skill_md(skill_name, content) (paia_builder/core.py:500)
    → self._ensure_current()
    → utils.find_component(paia, "skills", skill_name)
    → spec.skill_md = content
    → spec.updated = datetime.now()
    → self._save(paia)
    → if GIINT_AVAILABLE and git_dir:
      → utils.complete_task(paia.name, "skills", skill_name, "skill_md", "create_skill_md")
```

### POST /paiab/set/skill_reference (http_server.py:1100)
```
paiab_set_skill_reference(req)
  → builder.set_skill_reference(skill_name, content) (paia_builder/core.py:512)
    → [same pattern: find_component → spec.reference_md = content → save → giint]
```

### POST /paiab/set/skill_resource (http_server.py:1106)
```
paiab_set_skill_resource(req)
  → builder.add_skill_resource(skill_name, filename, content, content_type) (paia_builder/core.py:524)
    → [find_component → SkillResourceSpec(...) → spec.resources.append → save → giint]
```

### POST /paiab/set/mcp_server (http_server.py:1112)
```
paiab_set_mcp_server(req)
  → builder.set_mcp_server(mcp_name, content) (paia_builder/core.py:565)
    → [find_component → spec.server = OnionLayerSpec(...) → save → giint]
```

### POST /paiab/set/mcp_tool (http_server.py:1118)
```
paiab_set_mcp_tool(req)
  → builder.add_mcp_tool(mcp_name, core_function, ai_description) (paia_builder/core.py:577)
    → [find_component → MCPToolSpec(...) → spec.tools.append → save → giint]
```

### POST /paiab/set/hook_script (http_server.py:1124)
```
paiab_set_hook_script(req)
  → builder.set_hook_script(hook_name, content) (paia_builder/core.py:592)
    → [find_component → spec.script_content = content → save → giint]
```

### POST /paiab/set/command_prompt (http_server.py:1130)
```
paiab_set_command_prompt(req)
  → builder.set_command_prompt(cmd_name, content) (paia_builder/core.py:605)
    → [find_component → spec.prompt_content = content → save → giint]
```

### POST /paiab/set/agent_prompt (http_server.py:1136)
```
paiab_set_agent_prompt(req)
  → builder.set_agent_prompt(agent_name, content) (paia_builder/core.py:618)
    → [find_component → spec.system_prompt = content → save → giint]
```

### POST /paiab/set/persona_frame (http_server.py:1142)
```
paiab_set_persona_frame(req)
  → builder.set_persona_frame(persona_name, content) (paia_builder/core.py:631)
    → [find_component → spec.frame = content → save → giint]
```

### POST /paiab/set/flight_step (http_server.py:1148)
```
paiab_set_flight_step(req)
  → builder.add_flight_step(flight_name, step_number, title, instruction, skills_to_equip) (paia_builder/core.py:644)
    → [find_component → FlightStepSpec(...) → spec.steps.append → save → giint]
```

### POST /paiab/set/metastack_field (http_server.py:1154)
```
paiab_set_metastack_field(req)
  → builder.add_metastack_field(metastack_name, field_name, field_type, description, default) (paia_builder/core.py:663)
    → [find_component → MetastackFieldSpec(...) → spec.fields.append → save → giint]
```

---

## AGENT REGISTRY & RELAY ENDPOINTS

### POST /agents/register (http_server.py:1182)
```
register_agent(reg: AgentRegistration)
  → _agent_registry[reg.agent_id] = reg [dict assignment]
  → logger.info(...)
```

### DELETE /agents/{agent_id} (http_server.py:1190)
```
unregister_agent(agent_id: str)
  → if agent_id in _agent_registry:
    → del _agent_registry[agent_id] [dict delete]
  → else: return error
```

### GET /agents (http_server.py:1199)
```
list_agents()
  → {aid: reg.model_dump() for aid, reg in _agent_registry.items()} [pydantic]
```

### GET /agents/{agent_id} (http_server.py:1208)
```
get_agent(agent_id: str)
  → if agent_id not in _agent_registry: return error
  → _agent_registry[agent_id].model_dump() [pydantic]
```

### POST /agents/{agent_id}/execute (http_server.py:1216)
```
relay_execute(agent_id: str, req: RelayExecuteRequest)
  → if agent_id not in _agent_registry: return error
  → reg = _agent_registry[agent_id]
  → import httpx
  → async with httpx.AsyncClient() as client:
    → client.post(f"{reg.address}/execute", json={code, language, timeout}, timeout=timeout+5) [httpx]
    → resp.json()
  → on Exception: return error
```

### POST /agents/{agent_id}/interrupt (http_server.py:1237)
```
relay_interrupt(agent_id: str, double: bool = False)
  → if agent_id not in _agent_registry: return error
  → reg = _agent_registry[agent_id]
  → import httpx
  → async with httpx.AsyncClient() as client:
    → client.post(f"{reg.address}/interrupt", params={"double": double}, timeout=10) [httpx]
    → resp.json()
  → on Exception: return error
```

### POST /agents/{agent_id}/inject (http_server.py:1253)
```
relay_inject(agent_id: str, message: str, press_enter: bool = True)
  → if agent_id not in _agent_registry: return error
  → reg = _agent_registry[agent_id]
  → import httpx
  → async with httpx.AsyncClient() as client:
    → client.post(f"{reg.address}/self/inject", json={message, press_enter}, timeout=10) [httpx]
    → resp.json()
  → on Exception: return error
```

---

## AGENT MESSAGING ENDPOINTS (llegos-based)

### Helper: _get_agent (http_server.py:1304)
```
_get_agent(agent_id: str) -> Optional[CodeAgent]
  → if agent_id in _agent_instances: return _agent_instances[agent_id]
  → if agent_id in _agent_registry: return None [placeholder]
  → return None
```

### Helper: _serialize_message (http_server.py:1316)
```
_serialize_message(msg: Message) -> Dict
  → msg.id, msg.sender_id, msg.receiver_id, msg.parent_id [attr access]
  → getattr(msg, 'content', '') [attr access]
  → getattr(msg, 'priority', 0)
  → getattr(msg, 'ingress', IngressType.FRONTEND).value
  → msg.created_at.isoformat()
  → msg.metadata
```

### POST /messages/send (http_server.py:1331)
```
send_message(req: SendMessageRequest)
  → IngressType(req.ingress) [enum]
  → create_user_message(content, ingress, source_id, priority) (agent.py:438)
    → UserPromptMessage(content=..., ingress=..., source_id=..., priority=...)
  → msg.metadata.update(req.metadata) [dict]
  → msg.metadata["from_agent"] = req.from_agent
  → msg.metadata["to_agent"] = req.to_agent
  → _message_store[msg.id] = msg [dict]
  → _message_history.append(msg.id) [list]
  → if len > 1000: pop(0) + pop from store
  → target_agent = _get_agent(req.to_agent) (http_server.py:1304)
  → if target_agent:
    → target_agent.enqueue(msg) (agent.py:161)
      → if len >= max_inbox_size: self.emit("inbox:overflow", msg); return False
      → self._inbox.append(message) [deque]
      → self.emit("inbox:enqueued", message) [llegos Actor]
      → if state_file: self._save_inbox() (agent.py:374)
        → Path(state_file).write_text(json.dumps(data)) [stdlib]
  → if req.to_agent == "human" and _event_queue:
    → _event_queue.put_nowait({"type": "human_message", "data": _serialize_message(msg)})
  → logger.info(...)
```

### POST /messages/reply (http_server.py:1380)
```
reply_to_message(req: ReplyMessageRequest)
  → parent = _message_store.get(req.parent_message_id) [dict]
  → if not parent: return error
  → reply = parent.reply(content=req.content, priority=req.priority) [llegos Message.reply()]
  → reply.metadata.update(req.metadata) [dict]
  → _message_store[reply.id] = reply [dict]
  → _message_history.append(reply.id) [list]
  → if parent.sender:
    → target_agent = _get_agent(parent.sender_id) (http_server.py:1304)
    → if target_agent:
      → target_agent.enqueue(reply) (agent.py:161)
  → logger.info(...)
```

### GET /messages/thread/{message_id} (http_server.py:1409)
```
get_message_thread(message_id: str, height: int = 10)
  → msg = _message_store.get(message_id) [dict]
  → if not msg: return error
  → chain = list(message_chain(msg, height)) [llegos.llegos.message_chain]
    → [traverses msg.parent chain up to height]
  → [_serialize_message(m) for m in chain]
```

### GET /messages/{message_id} (http_server.py:1425)
```
get_message(message_id: str)
  → msg = _message_store.get(message_id) [dict]
  → if not msg: return error
  → _serialize_message(msg)
```

### GET /messages/inbox/{agent_id} (http_server.py:1434)
```
get_inbox(agent_id: str, unread: Optional[bool] = None)
  → agent = _get_agent(agent_id) (http_server.py:1304)
  → if agent:
    → for m in agent._inbox: [deque iteration]
      → _is_message_read_by(m.id, agent_id) (http_server.py:1830)
        → agent_id in _read_status.get(message_id, set())
      → filter by unread param
      → _serialize_message(m) + is_read
  → else [fallback]:
    → for mid in _message_history:
      → msg = _message_store[mid]
      → to_agent = msg.metadata.get("to_agent") or msg.receiver_id
      → filter by agent_id match
      → filter by unread param
      → _serialize_message(msg) + is_read
```

### GET /messages/inbox/{agent_id}/count (http_server.py:1471)
```
get_inbox_count(agent_id: str, unread: Optional[bool] = None)
  → agent = _get_agent(agent_id) (http_server.py:1304)
  → if agent:
    → if unread is None: return agent.inbox_count (agent.py:204)
      → len(self._inbox)
    → else: count with _is_message_read_by filter
  → else [fallback]:
    → iterate _message_history, count matches
```

### GET /messages/inbox/{agent_id}/peek (http_server.py:1509)
```
peek_inbox(agent_id: str)
  → agent = _get_agent(agent_id) (http_server.py:1304)
  → if agent:
    → msg = agent.peek() (agent.py:194)
      → if not self._inbox: return None
      → sorted(self._inbox, key=lambda m: (-m.priority, m.created_at))
      → return sorted_inbox[0]
    → if msg: _serialize_message(msg)
  → return None
```

### GET /messages/inbox/{agent_id}/pop (http_server.py:1520)
```
pop_message(agent_id: str)
  → agent = _get_agent(agent_id) (http_server.py:1304)
  → if agent:
    → msg = agent.dequeue() (agent.py:176)
      → if not self._inbox: return None
      → sorted(self._inbox, key=lambda m: (-m.priority, m.created_at))
      → message = sorted_inbox[0]
      → self._inbox.remove(message) [deque]
      → self.emit("inbox:dequeued", message) [llegos Actor]
      → return message
    → if msg: _serialize_message(msg)
  → return None
```

### DELETE /messages/inbox/{agent_id}/{message_id} (http_server.py:1531)
```
ack_message(agent_id: str, message_id: str)
  → agent = _get_agent(agent_id) (http_server.py:1304)
  → if agent:
    → for i, msg in enumerate(agent._inbox): [deque iteration]
      → if msg.id == message_id:
        → del agent._inbox[i] [deque delete]
        → return acknowledged
    → return error "not in inbox"
  → return error "agent not found"
```

### GET /messages/history (http_server.py:1545)
```
get_message_history(limit: int = 100, agent: Optional[str] = None)
  → history_ids = _message_history[-limit:] [list slice]
  → for mid in history_ids:
    → msg = _message_store[mid]
    → filter by agent match (sender_id or receiver_id)
    → _serialize_message(msg)
```

### POST /messages/forward (http_server.py:1570)
```
forward_message(req: ForwardMessageRequest)
  → original = _message_store.get(req.message_id) [dict]
  → if not original: return error
  → target_agent = _get_agent(req.to_agent) (http_server.py:1304)
  → if target_agent:
    → forwarded = original.forward_to(target_agent) [llegos Message.forward_to()]
  → else:
    → forwarded = original.forward_to(None) [llegos]
  → forwarded.metadata.update(req.metadata) [dict]
  → _message_store[forwarded.id] = forwarded [dict]
  → _message_history.append(forwarded.id) [list]
  → if target_agent:
    → target_agent.enqueue(forwarded) (agent.py:161)
  → logger.info(...)
```

### POST /agents/instance/register (http_server.py:1605)
```
register_agent_instance(agent_id: str, agent: CodeAgent)
  → _agent_instances[agent_id] = agent [dict]
```

### Internal: register_agent_instance_internal (http_server.py:1616)
```
register_agent_instance_internal(agent_id: str, agent: CodeAgent)
  → _agent_instances[agent_id] = agent [dict]
  → logger.info(...)
```

---

## THREAD ALIASING ENDPOINTS

### PUT /messages/thread/{message_id}/alias (http_server.py:1624)
```
set_thread_alias(message_id: str, req: ThreadAliasRequest)
  → msg = _message_store.get(message_id) [dict]
  → if not msg: return error
  → root = msg
  → while root.parent_id and root.parent_id in _message_store:
    → root = _message_store[root.parent_id] [traverses parent chain]
  → root.metadata["thread_alias"] = req.alias [dict]
```

### GET /messages/thread/{message_id}/alias (http_server.py:1650)
```
get_thread_alias(message_id: str)
  → msg = _message_store.get(message_id) [dict]
  → if not msg: return error
  → [traverse to root via parent_id chain]
  → alias = root.metadata.get("thread_alias")
```

### PUT /messages/thread/{message_id}/priority (http_server.py:1669)
```
set_thread_priority(message_id: str, priority: str = "normal")
  → if priority not in ("urgent", "normal", "low"): return error
  → msg = _message_store.get(message_id) [dict]
  → if not msg: return error
  → [traverse to root via parent_id chain]
  → root.metadata["thread_priority"] = priority [dict]
```

### DELETE /messages/thread/{message_id}/alias (http_server.py:1688)
```
delete_thread_alias(message_id: str)
  → msg = _message_store.get(message_id) [dict]
  → if not msg: return error
  → [traverse to root via parent_id chain]
  → old_alias = root.metadata.pop("thread_alias", None) [dict]
```

### GET /threads (http_server.py:1708)
```
list_threads(alias: Optional[str] = None)
  → seen_roots = set()
  → for msg_id in _message_history:
    → msg = _message_store[msg_id]
    → [traverse to root via parent_id chain]
    → if root.id in seen_roots: continue
    → seen_roots.add(root.id)
    → thread_alias = root.metadata.get("thread_alias")
    → if alias filter: check substring match
    → thread_count = sum(1 for mid in _message_history if _get_root_id(mid) == root.id)
      → _get_root_id(mid) (http_server.py:1755)
        → [traverse to root via parent_id chain]
    → {root_id, alias, message_count, created_at, preview}
```

---

## READ/UNREAD STATUS ENDPOINTS

### POST /messages/{message_id}/read (http_server.py:1767)
```
mark_message_read(message_id: str, agent_id: str)
  → if message_id not in _message_store: return error
  → if message_id not in _read_status:
    → _read_status[message_id] = set()
  → _read_status[message_id].add(agent_id) [set]
```

### DELETE /messages/{message_id}/read (http_server.py:1786)
```
mark_message_unread(message_id: str, agent_id: str)
  → if message_id not in _message_store: return error
  → if message_id in _read_status:
    → _read_status[message_id].discard(agent_id) [set]
```

### GET /messages/{message_id}/read_by (http_server.py:1802)
```
get_message_read_by(message_id: str)
  → if message_id not in _message_store: return error
  → readers = list(_read_status.get(message_id, set()))
```

### GET /messages/{message_id}/is_read (http_server.py:1816)
```
check_message_read(message_id: str, agent_id: str)
  → if message_id not in _message_store: return error
  → is_read = agent_id in _read_status.get(message_id, set()) [set]
```

---

## INTERNAL HELPERS (non-endpoint)

### _is_message_read_by (http_server.py:1830)
```
_is_message_read_by(message_id: str, agent_id: str) -> bool
  → agent_id in _read_status.get(message_id, set())
```

### unregister_agent_instance_internal (http_server.py:1835)
```
unregister_agent_instance_internal(agent_id: str)
  → if agent_id in _agent_instances:
    → del _agent_instances[agent_id] [dict]
  → logger.info(...)
```

### event_callback (http_server.py:139)
```
event_callback(event)
  → if _event_queue:
    → _event_queue.put_nowait({type, content, metadata}) [asyncio.Queue]
    → on QueueFull: pass (drop)
```

### event_generator (http_server.py:152)
```
event_generator()
  → [infinite async loop]
  → asyncio.wait_for(_event_queue.get(), timeout=30.0)
  → yield SSE data
  → on TimeoutError: yield keepalive
```

### get_paia (http_server.py:545)
```
get_paia(name: str)
  → _load_paia_store() (http_server.py:529)
    → PAIA_STORE_FILE.exists() [stdlib]
    → json.loads(PAIA_STORE_FILE.read_text()) [stdlib]
  → store.get(name)
  → if not paia_data: return None
  → from paia_builder.models import PAIA
  → PAIA.model_validate(paia_data) [pydantic]
```

### set_paia (http_server.py:558)
```
set_paia(name: str, paia)
  → _load_paia_store() (http_server.py:529)
  → store[name] = paia.model_dump(mode='json') [pydantic]
  → _save_paia_store(store) (http_server.py:539)
    → _ensure_store_dir() (http_server.py:524)
      → HEAVEN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    → PAIA_STORE_FILE.write_text(json.dumps(store)) [stdlib]
```

### _get_root_id (http_server.py:1755)
```
_get_root_id(msg_id: str) -> Optional[str]
  → if msg_id not in _message_store: return None
  → msg = _message_store[msg_id]
  → while msg.parent_id and msg.parent_id in _message_store:
    → msg = _message_store[msg.parent_id]
  → return msg.id
```

---

## ENDPOINT SUMMARY

| # | Method | Path | Handler | Line |
|---|--------|------|---------|------|
| 1 | POST | /spawn | spawn_agent | 165 |
| 2 | GET | /status | get_status | 187 |
| 3 | POST | /send | send_to_agent | 200 |
| 4 | POST | /inject | inject_event | 221 |
| 5 | POST | /event | push_event | 231 |
| 6 | GET | /events | events_stream | 261 |
| 7 | GET | /capture | capture_terminal | 283 |
| 8 | POST | /stop | stop_harness | 291 |
| 9 | GET | /hooks | get_hooks | 301 |
| 10 | POST | /hooks/{hook_type}/enable | enable_hook | 307 |
| 11 | POST | /hooks/{hook_type}/disable | disable_hook | 316 |
| 12 | POST | /hooks/{hook_type}/toggle | toggle_hook | 325 |
| 13 | GET | /persona | get_persona | 336 |
| 14 | POST | /persona/{name} | activate_persona | 345 |
| 15 | DELETE | /persona | deactivate_persona | 352 |
| 16 | POST | /self/restart | self_restart | 380 |
| 17 | POST | /self/compact | self_compact | 393 |
| 18 | POST | /self/inject | self_inject | 405 |
| 19 | POST | /execute | execute_code | 425 |
| 20 | POST | /interrupt | interrupt_claude | 461 |
| 21 | POST | /exit | exit_claude | 475 |
| 22 | POST | /force_exit | force_exit_claude | 485 |
| 23 | POST | /kill_agent_process | kill_agent_process | 495 |
| 24 | POST | /gear/accept | accept_gear_proof | 585 |
| 25 | POST | /gear/emit | emit_gear | 611 |
| 26 | GET | /gear/{paia_name} | get_gear_state | 626 |
| 27 | POST | /gear/register | register_paia | 649 |
| 28 | GET | /gear/list | list_registered_paias | 666 |
| 29 | GET | /cave/list | cave_list | 678 |
| 30 | GET | /cave/status | cave_status | 685 |
| 31 | GET | /cave/offers | cave_offers | 694 |
| 32 | GET | /cave/journeys | cave_journeys | 704 |
| 33 | GET | /sanctum/list | sanctum_list | 717 |
| 34 | GET | /sanctum/status | sanctum_status | 724 |
| 35 | GET | /sanctum/rituals | sanctum_rituals | 733 |
| 36 | GET | /sanctum/goals | sanctum_goals | 745 |
| 37 | GET | /paiab/list | paiab_list | 906 |
| 38 | GET | /paiab/status | paiab_status | 912 |
| 39 | GET | /paiab/which | paiab_which | 922 |
| 40 | POST | /paiab/select/{name} | paiab_select | 927 |
| 41 | POST | /paiab/new | paiab_new | 933 |
| 42 | DELETE | /paiab/{name} | paiab_delete | 939 |
| 43 | POST | /paiab/fork | paiab_fork | 945 |
| 44 | POST | /paiab/tick_version | paiab_tick_version | 951 |
| 45 | GET | /paiab/components/{comp_type} | paiab_list_components | 960 |
| 46 | GET | /paiab/component/{comp_type}/{name} | paiab_get_component | 969 |
| 47 | DELETE | /paiab/component/{comp_type}/{name} | paiab_remove_component | 974 |
| 48 | POST | /paiab/add/skill | paiab_add_skill | 983 |
| 49 | POST | /paiab/add/mcp | paiab_add_mcp | 989 |
| 50 | POST | /paiab/add/hook | paiab_add_hook | 995 |
| 51 | POST | /paiab/add/command | paiab_add_command | 1001 |
| 52 | POST | /paiab/add/agent | paiab_add_agent | 1007 |
| 53 | POST | /paiab/add/persona | paiab_add_persona | 1013 |
| 54 | POST | /paiab/add/plugin | paiab_add_plugin | 1019 |
| 55 | POST | /paiab/add/flight | paiab_add_flight | 1025 |
| 56 | POST | /paiab/add/metastack | paiab_add_metastack | 1031 |
| 57 | POST | /paiab/advance_tier | paiab_advance_tier | 1040 |
| 58 | POST | /paiab/set_tier | paiab_set_tier | 1046 |
| 59 | POST | /paiab/goldify | paiab_goldify | 1052 |
| 60 | POST | /paiab/regress_golden | paiab_regress_golden | 1058 |
| 61 | POST | /paiab/update_gear | paiab_update_gear | 1067 |
| 62 | POST | /paiab/sync_gear | paiab_sync_gear | 1073 |
| 63 | GET | /paiab/check_win | paiab_check_win | 1079 |
| 64 | POST | /paiab/publish | paiab_publish | 1085 |
| 65 | POST | /paiab/set/skill_md | paiab_set_skill_md | 1094 |
| 66 | POST | /paiab/set/skill_reference | paiab_set_skill_reference | 1100 |
| 67 | POST | /paiab/set/skill_resource | paiab_set_skill_resource | 1106 |
| 68 | POST | /paiab/set/mcp_server | paiab_set_mcp_server | 1112 |
| 69 | POST | /paiab/set/mcp_tool | paiab_set_mcp_tool | 1118 |
| 70 | POST | /paiab/set/hook_script | paiab_set_hook_script | 1124 |
| 71 | POST | /paiab/set/command_prompt | paiab_set_command_prompt | 1130 |
| 72 | POST | /paiab/set/agent_prompt | paiab_set_agent_prompt | 1136 |
| 73 | POST | /paiab/set/persona_frame | paiab_set_persona_frame | 1142 |
| 74 | POST | /paiab/set/flight_step | paiab_set_flight_step | 1148 |
| 75 | POST | /paiab/set/metastack_field | paiab_set_metastack_field | 1154 |
| 76 | POST | /agents/register | register_agent | 1182 |
| 77 | DELETE | /agents/{agent_id} | unregister_agent | 1190 |
| 78 | GET | /agents | list_agents | 1199 |
| 79 | GET | /agents/{agent_id} | get_agent | 1208 |
| 80 | POST | /agents/{agent_id}/execute | relay_execute | 1216 |
| 81 | POST | /agents/{agent_id}/interrupt | relay_interrupt | 1237 |
| 82 | POST | /agents/{agent_id}/inject | relay_inject | 1253 |
| 83 | POST | /messages/send | send_message | 1331 |
| 84 | POST | /messages/reply | reply_to_message | 1380 |
| 85 | GET | /messages/thread/{message_id} | get_message_thread | 1409 |
| 86 | GET | /messages/{message_id} | get_message | 1425 |
| 87 | GET | /messages/inbox/{agent_id} | get_inbox | 1434 |
| 88 | GET | /messages/inbox/{agent_id}/count | get_inbox_count | 1471 |
| 89 | GET | /messages/inbox/{agent_id}/peek | peek_inbox | 1509 |
| 90 | GET | /messages/inbox/{agent_id}/pop | pop_message | 1520 |
| 91 | DELETE | /messages/inbox/{agent_id}/{message_id} | ack_message | 1531 |
| 92 | GET | /messages/history | get_message_history | 1545 |
| 93 | POST | /messages/forward | forward_message | 1570 |
| 94 | POST | /agents/instance/register | register_agent_instance | 1605 |
| 95 | PUT | /messages/thread/{message_id}/alias | set_thread_alias | 1624 |
| 96 | GET | /messages/thread/{message_id}/alias | get_thread_alias | 1650 |
| 97 | PUT | /messages/thread/{message_id}/priority | set_thread_priority | 1669 |
| 98 | DELETE | /messages/thread/{message_id}/alias | delete_thread_alias | 1688 |
| 99 | GET | /threads | list_threads | 1708 |
| 100 | POST | /messages/{message_id}/read | mark_message_read | 1767 |
| 101 | DELETE | /messages/{message_id}/read | mark_message_unread | 1786 |
| 102 | GET | /messages/{message_id}/read_by | get_message_read_by | 1802 |
| 103 | GET | /messages/{message_id}/is_read | check_message_read | 1816 |

**Total: 103 endpoints** (not 73 as originally estimated)

---

## FILES TRACED

| File | Path | Purpose |
|------|------|---------|
| http_server.py | .../harness/server/http_server.py | Main FastAPI server (1843 lines) |
| harness.py | .../harness/core/harness.py | PAIAHarness - tmux control plane (380 lines) |
| hook_control.py | .../harness/core/hook_control.py | HookControl - file-based hook toggling (87 lines) |
| persona_control.py | .../harness/core/persona_control.py | PersonaControl - file-based persona flag (35 lines) |
| self_command_generator.py | .../harness/core/self_command_generator.py | SelfCommandGenerator - bash script generation (212 lines) |
| agent.py | .../harness/core/agent.py | CodeAgent - llegos Actor with inbox (487 lines) |
| event_router.py | .../harness/core/event_router.py | EventRouter - terminal/hook/SSE routing (383 lines) |
| gear_events.py | .../harness/events/gear_events.py | GEAR event bus - bidirectional (388 lines) |
| core.py (cave) | /tmp/cave-builder/cave_builder/core.py | CAVEBuilder - business domain (302 lines) |
| core.py (sanctum) | /tmp/sanctum-builder/sanctum_builder/core.py | SANCTUMBuilder - life architecture (500 lines) |
| core.py (paia) | /tmp/paia-builder/paia_builder/core.py | PAIABuilder - PAIA construction (737 lines) |

**External dependencies**: llegos (Actor model), httpx (relay), pydantic (models), fastapi, subprocess, asyncio, tmux
