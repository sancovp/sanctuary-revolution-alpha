# CAVE HTTP Server - Deep Callgraph Trace

> Traced from `/tmp/cave/cave/server/http_server.py`
> All paths traced to stdlib / well-known external packages.

---

## TABLE OF CONTENTS

1. [Server Startup & Shutdown](#1-server-startup--shutdown)
2. [Config Archive Endpoints](#2-config-archive-endpoints)
3. [Loop Manager Endpoints](#3-loop-manager-endpoints)
4. [DNA (Auto Mode) Endpoints](#4-dna-auto-mode-endpoints)
5. [Module Hot-Load Endpoints](#5-module-hot-load-endpoints)
6. [Hook Signal Endpoints](#6-hook-signal-endpoints)
7. [Omnisanc Endpoints](#7-omnisanc-endpoints)
8. [Metabrainhook Endpoints](#8-metabrainhook-endpoints)
9. [PAIA Mode Control Endpoints](#9-paia-mode-control-endpoints)
10. [Live Mirror Endpoints](#10-live-mirror-endpoints)
11. [Inbox Endpoints](#11-inbox-endpoints)
12. [PAIA State Endpoints](#12-paia-state-endpoints)
13. [Remote Agent Endpoints](#13-remote-agent-endpoints)
14. [SSE Events Endpoint](#14-sse-events-endpoint)
15. [Health Endpoint](#15-health-endpoint)
16. [Dependency Summary](#16-dependency-summary)

---

## IMPORTS AT SERVER LEVEL

```
http_server.py imports:
  argparse                              [stdlib]
  typing.Any, Dict                      [stdlib]
  fastapi.FastAPI                       [fastapi - external]
  starlette.responses.StreamingResponse [starlette - external]
  cave.core.cave_agent.CAVEAgent        [/tmp/cave/cave/core/cave_agent.py]
  cave.core.config.CAVEConfig           [/tmp/cave/cave/core/config.py]
  cave.core.state_reader.ClaudeStateReader [/tmp/cave/cave/core/state_reader.py]
```

---

## 1. SERVER STARTUP & SHUTDOWN

### `startup()` [http_server.py:27]

```
@app.on_event("startup")
async def startup():
  → CAVEConfig.load() [config.py:76]
    → Path(CAVE_AGENT_CONFIG_PATH).exists() [pathlib - stdlib]
    → json.loads(file.read_text()) [json - stdlib, pathlib - stdlib]
    → cls.model_validate(data) [pydantic - external]
    → (if restart_config) json.loads(archive_path.read_text()) [json - stdlib]
    → cls.model_validate(archive_data) [pydantic - external]
    → (if no file) cls() → config.save() [below]
      → CAVEConfig.save() [config.py:63]
        → CAVE_AGENT_CONFIG_PATH.parent.mkdir() [pathlib - stdlib]
        → CAVE_AGENT_CONFIG_PATH.write_text(self.model_dump_json()) [pathlib - stdlib, pydantic - external]

  → CAVEAgent.__init__(config) [cave_agent.py:48]
    → self.config = config [pydantic CAVEConfig]
    → self.paia_states = {} [dict - stdlib]
    → self.agent_registry = {} [dict - stdlib]
    → self.remote_agents = {} [dict - stdlib]

    → ClaudeStateReader(project_dir=...) [state_reader.py:22]
      → dataclass __post_init__ [dataclasses - stdlib]
      → Path(self.claude_home), Path(self.project_dir) [pathlib - stdlib]

    → self._attach_to_session() [cave_agent.py:109]
      → subprocess.run(["tmux", "has-session", "-t", session]) [subprocess - stdlib]
      → (if exists) ClaudeCodeAgentConfig(agent_command=..., tmux_session=...) [agent.py:471]
      → ClaudeCodeAgent(config=agent_config) [agent.py:477]
        → CodeAgent.__init__() [agent.py:148]
          → Actor.__init__() [llegos.py:123]
            → Object.__init__() [pydantic BaseModel]
              → namespaced_ksuid_generator("actor")() [ksuid - external]
          → deque(maxlen=max_inbox_size) [collections.deque - stdlib]
          → (if state_file) self._load_inbox() [agent.py:389]
            → Path(state_file).exists() [pathlib - stdlib]
            → json.loads(file.read_text()) [json - stdlib]
            → InboxMessage(**msg_data) [pydantic BaseModel]
      → self._emit_event("attached"|"no_session", ...) [SSEMixin._emit_event, sse.py:20]
        → asyncio.Queue.put_nowait(event) [asyncio - stdlib]

    → self._init_hook_router() [HookRouterMixin, hook_router.py:27]
      → HookRegistry(self.config.hook_dir) [hooks.py:174]
        → self.hooks_dir = hooks_dir [pathlib - stdlib]
        → self._registry = {} [dict - stdlib]
        → self._scripts = {} [dict - stdlib]
        → self._scripts_config_path = hooks_dir / "scripts.json" [pathlib - stdlib]
      → hook_registry.scan() [hooks.py:182]
        → hooks_dir.glob("*.py") [pathlib - stdlib]
        → _load_entry(py_file) [hooks.py:230]
          → importlib.util.spec_from_file_location() [importlib - stdlib]
          → importlib.util.module_from_spec() [importlib - stdlib]
          → spec.loader.exec_module() [importlib - stdlib]
          → inspect.getmembers(module) [inspect - stdlib]
          → (finds ClaudeCodeHook subclasses)
      → hook_registry.load_scripts_config() [hooks.py:392]
        → _scripts_config_path.exists() [pathlib - stdlib]
        → json.loads(file.read_text()) [json - stdlib]
        → register_script(name, hook_type, path) [hooks.py:338]
          → ScriptHookAdapter(name, hook_type, script_path) [hooks.py:97]

    → self._init_loop_manager() [LoopManagerMixin, loop_manager.py:27]
      → self._loop_state = {...} [dict - stdlib]
      → self._active_loop = None

    → self._init_sse() [SSEMixin, sse.py:16]
      → asyncio.Queue(maxsize=1000) [asyncio - stdlib]

    → self._init_omnisanc() [OmnisancMixin, omnisanc.py:25]
      → OMNISANC_STATE_FILE.parent.mkdir() [pathlib - stdlib]
      → METABRAINHOOK_PROMPT_FILE.parent.mkdir() [pathlib - stdlib]

    → self._init_anatomy() [AnatomyMixin, anatomy.py:181]
      → self.organs = {} [dict - stdlib]
      → Heart(name="main_heart") [anatomy.py:47]
        → (if SDNA_AVAILABLE) HeartbeatScheduler() [sdna - external, optional]
      → Blood() [anatomy.py:116]
        → self._payload = {} [dict - stdlib]
        → self._flow_history = [] [list - stdlib]

    → self.dna = None [AutoModeDNA, optional]

    → (if system_prompt_template_path) self._render_system_prompt() [cave_agent.py:99]
      → template_path.read_text() [pathlib - stdlib]
      → str.replace("{{key}}", value) [str - stdlib]
      → target_path.parent.mkdir() [pathlib - stdlib]
      → target_path.write_text(rendered) [pathlib - stdlib]

    → self.config.data_dir.mkdir() [pathlib - stdlib]
    → self.config.hook_dir.mkdir() [pathlib - stdlib]

    → MainAgentConfigManager(data_dir, claude_home) [config_snapshots.py:23]
      → self.archives_dir = data_dir / "config_archives" [pathlib - stdlib]
      → archives_dir.mkdir() [pathlib - stdlib]
```

### `shutdown()` [http_server.py:34]

```
async def shutdown():
  → pass (no-op)
```

---

## 2. CONFIG ARCHIVE ENDPOINTS

### `GET /configs` [http_server.py:40]

```
→ cave.list_config_archives() [cave_agent.py:193]
  → self.config_manager.list_archives() [config_snapshots.py:209]
    → self.archives_dir.iterdir() [pathlib - stdlib]
    → (for each dir) json.loads((dir / "_metadata.json").read_text()) [json/pathlib - stdlib]
    → self._get_active_config() [config_snapshots.py:233]
      → self.active_file.exists() [pathlib - stdlib]
      → json.loads(active_file.read_text()) [json - stdlib]
```

### `GET /configs/active` [http_server.py:46]

```
→ cave.get_active_config() [cave_agent.py:197]
  → self.config_manager.get_active_info() [config_snapshots.py:240]
    → self._detect_matching_archive() [config_snapshots.py:77]
      → self._compute_config_hash(self.claude_home) [config_snapshots.py:54]
        → (claude_home / rel_path).exists() [pathlib - stdlib]
        → file.read_bytes() [pathlib - stdlib]
        → hashlib.sha256() [hashlib - stdlib]
        → hasher.update() / hexdigest() [hashlib - stdlib]
      → (for each archive) self._compute_config_hash(archive_dir) [same as above]
    → (if no match) self.active_file.exists() [pathlib - stdlib]
    → json.loads(active_file.read_text()) [json - stdlib]
```

### `POST /configs/archive` [http_server.py:52]

```
→ cave.archive_config(name) [cave_agent.py:179]
  → self.config_manager.archive(name) [config_snapshots.py:89]
    → archive_path = archives_dir / name [pathlib - stdlib]
    → archive_path.exists() [pathlib - stdlib]
    → archive_path.mkdir() [pathlib - stdlib]
    → (for each config_file) shutil.copy2(src, dst) [shutil - stdlib]
    → (for each config_dir) shutil.copytree(src, dst) [shutil - stdlib]
    → json.dumps(metadata) [json - stdlib]
    → (archive_path / "_metadata.json").write_text() [pathlib - stdlib]
  → self._emit_event("config_archived", ...) [SSEMixin, sse.py:20]
    → asyncio.Queue.put_nowait() [asyncio - stdlib]
```

### `POST /configs/inject` [http_server.py:61]

```
→ cave.inject_config(name) [cave_agent.py:186]
  → self.config_manager.inject(name) [config_snapshots.py:148]
    → archive_path.exists() [pathlib - stdlib]
    → self.archive(backup_name) [same as archive above]
    → (for each file) shutil.copy2(src, dst) [shutil - stdlib]
    → (for each dir) shutil.rmtree(dst), shutil.copytree(src, dst) [shutil - stdlib]
    → active_file.write_text(json.dumps(active_info)) [json/pathlib - stdlib]
  → self._emit_event("config_injected", ...) [SSEMixin]
```

### `DELETE /configs/{name}` [http_server.py:69]

```
→ cave.delete_config_archive(name) [cave_agent.py:201]
  → self.config_manager.delete_archive(name) [config_snapshots.py:265]
    → shutil.rmtree(archive_path) [shutil - stdlib]
```

### `POST /configs/export` [http_server.py:76]

```
→ cave.export_config_archive(name, dest_path) [cave_agent.py:205]
  → self.config_manager.export_archive(name, dest_path) [config_snapshots.py:274]
    → shutil.copytree(archive_path, dest) [shutil - stdlib]
```

### `POST /configs/import` [http_server.py:86]

```
→ cave.import_config_archive(source_path, name) [cave_agent.py:209]
  → self.config_manager.import_archive(source_path, name) [config_snapshots.py:287]
    → shutil.copytree(source, archive_path) [shutil - stdlib]
```

---

## 3. LOOP MANAGER ENDPOINTS

### `GET /loops/state` [http_server.py:97]

```
→ cave.get_loop_state() [LoopManagerMixin, loop_manager.py:37]
  → returns self._loop_state dict + AVAILABLE_LOOPS keys [dict - stdlib]
  → (if active) accesses loop.name, loop.description, loop.active_hooks [dataclass fields]
```

### `POST /loops/start` [http_server.py:103]

```
→ cave.start_loop(loop_type, config) [LoopManagerMixin, loop_manager.py:49]
  → (if active) self.stop_loop() [loop_manager.py:95] (see below)
  → AVAILABLE_LOOPS[loop_type] [loops/__init__.py:25]
    → AgentInferenceLoop instances defined in:
      → autopoiesis.py (AUTOPOIESIS_LOOP)
      → guru.py (GURU_LOOP)
      → omnisanc_loops.py (OMNISANC_* loops)
  → loop.activate(self) [loops/base.py:60]
    → cave_agent.config.main_agent_config.active_hooks = self.active_hooks.copy() [dict - stdlib]
    → (if prompt & main_agent) cave_agent.main_agent.send_keys(prompt, 0.5, "Enter") [agent.py:254]
      → CodeAgent.send_keys(*sequence) [agent.py:254]
        → time.sleep(item) [time - stdlib] (for float args)
        → self._run_tmux("send-keys", "-t", session, item) [agent.py:216]
          → subprocess.run(["tmux", "send-keys", "-t", session, text]) [subprocess - stdlib]
    → (if on_start) loop.on_start(state) [callback function]
      → autopoiesis._on_start: sets state["autopoiesis"] dict [autopoiesis.py:11]
      → guru._on_start: sets state["guru"] dict [guru.py:13]
  → self._hook_state["_loop_config"] = config [dict - stdlib]
  → (if on_start) loop.on_start(self._hook_state) [callback - same as above]
```

### `POST /loops/stop` [http_server.py:111]

```
→ cave.stop_loop() [LoopManagerMixin, loop_manager.py:95]
  → (if on_stop) loop.on_stop(state) [callback]
    → autopoiesis._on_stop: sets state["autopoiesis"]["mode"] = "stopped" [autopoiesis.py:19]
    → guru._on_stop: sets state["guru"]["mode"] = "stopped" [guru.py:21]
  → loop.deactivate(self) [loops/base.py:89]
    → cave_agent.config.main_agent_config.active_hooks = {} [dict - stdlib]
    → (if on_stop) loop.on_stop(state) [callback]
  → clears self._active_loop, self._loop_state [dict - stdlib]
```

### `POST /loops/trigger` [http_server.py:117]

```
→ cave.trigger_transition(event, data) [LoopManagerMixin, loop_manager.py:128]
  → (for each condition) condition_fn(self._hook_state) [callable - user-defined]
  → transitions dict lookup [dict - stdlib]
  → updates self._loop_state [dict - stdlib]
```

### `POST /loops/pause` [http_server.py:124]

```
→ cave.pause_loop() [LoopManagerMixin, loop_manager.py:164]
  → self._hook_state[loop.name]["paused"] = True [dict - stdlib]
  → self._loop_state["mode"] = "paused" [dict - stdlib]
```

### `POST /loops/resume` [http_server.py:130]

```
→ cave.resume_loop() [LoopManagerMixin, loop_manager.py:174]
  → self._hook_state[loop.name]["paused"] = False [dict - stdlib]
  → self._loop_state["mode"] = "working" [dict - stdlib]
```

### `GET /loops/available` [http_server.py:136]

```
→ cave.list_available_loops() [LoopManagerMixin, loop_manager.py:184]
  → iterates AVAILABLE_LOOPS [loops/__init__.py:25]
  → reads .description, .active_hooks, .conditions from AgentInferenceLoop [dataclass fields]
```

---

## 4. DNA (AUTO MODE) ENDPOINTS

### `GET /dna/status` [http_server.py:143]

```
→ cave.get_dna_status() [cave_agent.py:234]
  → (if no dna) returns {"status": "no_dna"}
  → self.dna.get_status() [dna.py:208]
    → returns dict with name, active, exit_behavior, current_index, loop_names [dataclass fields]
```

### `POST /dna/start` [http_server.py:149]

```
→ (inline import) from cave.core.dna import create_dna [dna.py:221]
→ create_dna(name, loop_names, exit_behavior) [dna.py:221]
  → AVAILABLE_LOOPS[loop_name] for each name [loops/__init__.py:25]
  → AutoModeDNA(name, loops, ExitBehavior(exit_behavior)) [dna.py:27]
→ cave.start_auto_mode(dna) [cave_agent.py:215]
  → self.dna = dna
  → self.dna.start(self) [dna.py:58]
    → self.loops[0].activate(cave_agent) [loops/base.py:60]
      → (sets active_hooks, sends prompt via tmux — see POST /loops/start)
```

### `POST /dna/stop` [http_server.py:166]

```
→ cave.stop_auto_mode() [cave_agent.py:220]
  → self.dna.stop(self) [dna.py:78]
    → self.current_loop.deactivate(cave_agent) [loops/base.py:89]
      → clears active_hooks [dict - stdlib]
      → calls on_stop callback if present
  → self.dna = None
```

---

## 5. MODULE HOT-LOAD ENDPOINTS

### `GET /modules` [http_server.py:173]

```
→ cave.list_modules()
  → (method not found in traced code — likely from a mixin not yet loaded or TODO)
```

### `POST /modules/load` [http_server.py:179]

```
→ cave.load_module(name, code)
  → (method not found in traced code)
```

### `POST /modules/unload` [http_server.py:189]

```
→ cave.unload_module(name)
  → (method not found in traced code)
```

### `GET /modules/history` [http_server.py:198]

```
→ cave.get_module_history()
  → (method not found in traced code)
```

> **NOTE**: Module hot-load methods (`list_modules`, `load_module`, `unload_module`, `get_module_history`) are referenced in http_server.py but not defined in the traced CAVEAgent class or any of its 10 mixins. These are likely defined in a mixin or file not yet integrated, or are TODO stubs that would raise AttributeError at runtime.

---

## 6. HOOK SIGNAL ENDPOINTS

### `POST /hook/{hook_type}` [http_server.py:204]

```
→ cave.run_omnisanc() [cave_agent.py:242]
  → self.is_omnisanc_enabled() [OmnisancMixin, omnisanc.py:92]
    → OMNISANC_DISABLED_FILE.exists() [pathlib - stdlib]
  → self.get_omnisanc_state() [OmnisancMixin, omnisanc.py:35]
    → json.loads(OMNISANC_STATE_FILE.read_text()) [json/pathlib - stdlib]
  → self.get_paia_mode() [cave_agent.py:308]
    → Path("/tmp/heaven_data/paia_mode.txt").read_text() [pathlib - stdlib]
  → self.get_auto_mode() [cave_agent.py:323]
    → Path("/tmp/heaven_data/paia_auto.txt").read_text() [pathlib - stdlib]
  → zone detection logic [python logic]
  → self.config.main_agent_config.active_hooks = {...} [dict - stdlib]

→ cave.handle_hook(hook_type, data) [HookRouterMixin, hook_router.py:37]
  → payload.pop("source", "claude_code") [dict - stdlib]
  → (if openclaw) self._normalize_openclaw_payload() [hook_router.py:159]
    → payload dict remapping [dict - stdlib]
  → self.config.main_agent_config.active_hooks.get(hook_type_lower, []) [dict - stdlib]
  → self._hook_history.append(event) [list - stdlib]
  → self.hook_registry.get_hooks_for_type(hook_type_lower) [hooks.py:285]
    → iterates self._registry (class-based hooks) [dict - stdlib]
    → lazy instantiation: entry.hook_class() [ClaudeCodeHook subclass]
    → iterates self._scripts (ScriptHookAdapters) [dict - stdlib]
  → get_capability_context_for_hook(hook_type, payload, enabled) [capability_resolver.py:98]
    → extract_query_from_hook_payload(payload) [capability_resolver.py:70]
      → dict.get() operations [dict - stdlib]
    → resolve_capabilities(query, compact=True) [capability_resolver.py:48]
      → _get_rag_module() [capability_resolver.py:18]
        → (try) from capability_predictor import unified_rag [external, optional]
        → (fallback) importlib.util.spec_from_file_location() [importlib - stdlib]
      → rag.get_capability_context(query, compact) [external, optional]
  → (for each matching hook) hook(payload, self._hook_state) [callable]
    → ClaudeCodeHook.__call__() [hooks.py:83]
      → self.handle(payload, state) → HookResult [abstract, user-defined]
      → HookResult.to_dict() [hooks.py:38]
    → OR ScriptHookAdapter.__call__() [hooks.py:110]
      → subprocess.run(["python3", script_path], input=json.dumps(payload)) [subprocess/json - stdlib]
      → json.loads(result.stdout) [json - stdlib]
  → (if block) returns block response [dict - stdlib]
  → self.check_dna_transition() [cave_agent.py:228]
    → self.dna.check_and_transition(self) [dna.py:93]
      → loop.check_exit(state) [loops/base.py:110]
        → exit_condition(state) [callable - user-defined]
          → autopoiesis: Path("/tmp/active_promise.md").exists() [pathlib - stdlib]
          → guru: state.get("guru", {}).get("emanation_created") [dict - stdlib]
          → omnisanc: state.get("omnisanc_zone") != target_zone [dict - stdlib]
      → loop.deactivate(cave_agent) [loops/base.py:89]
      → (if next is str) find loop by name [list iteration]
      → (if next is TransitionAction) from sdna import ContextEngineeringLib, ActivateLoop [external, optional]
        → next_target.execute_chain(lib) [sdna - external]
      → next_loop.activate(cave_agent) [loops/base.py:60] (see POST /loops/start)
```

### `POST /hooks/scan` [http_server.py:218]

```
→ cave.scan_hooks() [HookRouterMixin, hook_router.py:128]
  → self.hook_registry.scan() [hooks.py:182] (see startup trace)
```

### `GET /hooks` [http_server.py:224]

```
→ cave.list_hooks() [HookRouterMixin, hook_router.py:132]
  → self.hook_registry.list() [hooks.py:318]
    → dict comprehension over self._registry [dict - stdlib]
```

### `GET /hooks/status` [http_server.py:230]

```
→ cave.get_hook_status() [HookRouterMixin, hook_router.py:148]
  → self.hook_registry.list() [hooks.py:318] (see above)
  → HookControl.get_all() [hook_control.py:74]
    → HookControl._load() [hook_control.py:34]
      → HOOK_CONTROL_CONFIG.exists() [pathlib - stdlib]
      → json.loads(file.read_text()) [json - stdlib]
```

### `GET /hooks/active` [http_server.py:236]

```
→ cave.config.main_agent_config.active_hooks [models.py:21, pydantic field]
  → dict access [dict - stdlib]
```

### `POST /hooks/active` [http_server.py:242]

```
→ cave.config.main_agent_config.active_hooks = data [pydantic model field assignment]
→ cave.config.save() [config.py:63]
  → CAVE_AGENT_CONFIG_PATH.write_text(self.model_dump_json()) [pathlib - stdlib, pydantic - external]
→ cave.scan_hooks() [hook_router.py:128] (see above)
```

---

## 7. OMNISANC ENDPOINTS

### `GET /omnisanc/state` [http_server.py:252]

```
→ cave.get_omnisanc_state() [OmnisancMixin, omnisanc.py:35]
  → OMNISANC_STATE_FILE.exists() [pathlib - stdlib]
    → Path("/tmp/heaven_data/omnisanc_core/.course_state")
  → json.loads(file.read_text()) [json/pathlib - stdlib]
```

### `GET /omnisanc/status` [http_server.py:258]

```
→ cave.get_omnisanc_status() [OmnisancMixin, omnisanc.py:219]
  → self.is_omnisanc_enabled() [omnisanc.py:92]
    → OMNISANC_DISABLED_FILE.exists() [pathlib - stdlib]
  → self.get_omnisanc_zone() [omnisanc.py:57]
    → self.get_omnisanc_state() [see above]
    → zone logic (HOME/STARPORT/LAUNCH/SESSION/LANDING/MISSION) [python logic]
  → self.is_home() [omnisanc.py:80]
  → METABRAINHOOK_PROMPT_FILE.exists() [pathlib - stdlib]
  → self.get_metabrainhook_state() [omnisanc.py:141] (see metabrainhook section)
```

### `GET /omnisanc/zone` [http_server.py:264]

```
→ cave.get_omnisanc_zone() [OmnisancMixin, omnisanc.py:57]
  → self.get_omnisanc_state() [see above]
  → zone detection logic [python logic]
```

### `GET /omnisanc/enabled` [http_server.py:270]

```
→ cave.is_omnisanc_enabled() [OmnisancMixin, omnisanc.py:92]
  → OMNISANC_DISABLED_FILE.exists() [pathlib - stdlib]
    → Path("/tmp/heaven_data/omnisanc_core/.omnisanc_disabled")
```

### `POST /omnisanc/enable` [http_server.py:276]

```
→ cave.enable_omnisanc() [OmnisancMixin, omnisanc.py:99]
  → self.is_omnisanc_enabled() [see above]
  → OMNISANC_DISABLED_FILE.unlink() [pathlib - stdlib]
```

### `POST /omnisanc/disable` [http_server.py:282]

```
→ cave.disable_omnisanc() [OmnisancMixin, omnisanc.py:118]
  → self.is_omnisanc_enabled() [see above]
  → OMNISANC_DISABLED_FILE.parent.mkdir() [pathlib - stdlib]
  → OMNISANC_DISABLED_FILE.write_text("disabled") [pathlib - stdlib]
```

---

## 8. METABRAINHOOK ENDPOINTS

### `GET /metabrainhook/state` [http_server.py:288]

```
→ cave.get_metabrainhook_state() [OmnisancMixin, omnisanc.py:141]
  → METABRAINHOOK_STATE_FILE.exists() [pathlib - stdlib]
    → Path("/tmp/metabrainhook_state.txt")
  → file.read_text().strip().lower() == "on" [pathlib - stdlib, str - stdlib]
```

### `POST /metabrainhook/state` [http_server.py:294]

```
→ cave.set_metabrainhook_state(on) [OmnisancMixin, omnisanc.py:150]
  → self.get_metabrainhook_state() [see above]
  → METABRAINHOOK_STATE_FILE.write_text("on"|"off") [pathlib - stdlib]
```

### `GET /metabrainhook/prompt` [http_server.py:301]

```
→ cave.get_metabrainhook_prompt() [OmnisancMixin, omnisanc.py:179]
  → METABRAINHOOK_PROMPT_FILE.exists() [pathlib - stdlib]
    → Path("/tmp/heaven_data/metabrainhook_config.json")
  → file.read_text() [pathlib - stdlib]
```

### `POST /metabrainhook/prompt` [http_server.py:308]

```
→ cave.set_metabrainhook_prompt(content) [OmnisancMixin, omnisanc.py:191]
  → METABRAINHOOK_PROMPT_FILE.parent.mkdir() [pathlib - stdlib]
  → METABRAINHOOK_PROMPT_FILE.write_text(content) [pathlib - stdlib]
```

---

## 9. PAIA MODE CONTROL ENDPOINTS

### `GET /paia/mode` [http_server.py:317]

```
→ cave.get_paia_mode() [cave_agent.py:308]
  → Path("/tmp/heaven_data/paia_mode.txt").exists() [pathlib - stdlib]
  → file.read_text().strip().upper() [pathlib/str - stdlib]
→ cave.get_auto_mode() [cave_agent.py:323]
  → Path("/tmp/heaven_data/paia_auto.txt").exists() [pathlib - stdlib]
  → file.read_text().strip().upper() [pathlib/str - stdlib]
```

### `POST /paia/mode` [http_server.py:326]

```
→ cave.set_paia_mode(mode) [cave_agent.py:349]
  → mode.upper() [str - stdlib]
  → Path("/tmp/heaven_data/paia_mode.txt").parent.mkdir() [pathlib - stdlib]
  → file.write_text(mode) [pathlib - stdlib]
```

### `POST /paia/auto` [http_server.py:333]

```
→ cave.set_auto_mode(mode) [cave_agent.py:338]
  → mode.upper() [str - stdlib]
  → Path("/tmp/heaven_data/paia_auto.txt").parent.mkdir() [pathlib - stdlib]
  → file.write_text(mode) [pathlib - stdlib]
```

---

## 10. LIVE MIRROR ENDPOINTS

### `GET /output` [http_server.py:347]

```
→ cave._ensure_attached() [cave_agent.py:126]
  → self.main_agent.session_exists() [agent.py:221]
    → self._run_tmux("has-session", "-t", session) [agent.py:216]
      → subprocess.run(["tmux", "has-session", "-t", session]) [subprocess - stdlib]
  → (if not) self._attach_to_session() [cave_agent.py:109] (see startup)
→ cave.main_agent.capture_pane(history_limit=lines) [agent.py:265]
  → self._run_tmux("capture-pane", "-t", session, "-p", "-S", f"-{history_limit}") [agent.py:216]
    → subprocess.run(["tmux", "capture-pane", "-t", session, "-p", "-S", limit]) [subprocess - stdlib]
→ ClaudeStateReader.parse_context_pct(output) [state_reader.py:316]
  → re.search(pattern, output, re.IGNORECASE) [re - stdlib]
```

### `POST /input` [http_server.py:356]

```
→ cave._ensure_attached() [see above]
→ cave.main_agent.send_keys(text, "Enter") [agent.py:254]
  → self._run_tmux("send-keys", "-t", session, text) [agent.py:216]
    → subprocess.run(["tmux", "send-keys", "-t", session, text]) [subprocess - stdlib]
  → self._run_tmux("send-keys", "-t", session, "Enter") [agent.py:216]
    → subprocess.run(["tmux", "send-keys", "-t", session, "Enter"]) [subprocess - stdlib]
```

### `GET /state` [http_server.py:369]

```
→ cave._ensure_attached() [see above]
→ cave.main_agent.capture_pane(lines=50) [agent.py:265] (see GET /output)
→ ClaudeStateReader.parse_context_pct(output) [state_reader.py:316] (see above)
→ cave.state_reader.get_complete_state() [state_reader.py:291]
  → self.read_settings() [state_reader.py:39]
    → (claude_home / "settings.json").exists() [pathlib - stdlib]
    → json.loads(file.read_text()) [json/pathlib - stdlib]
  → self.read_settings_local() [state_reader.py:49]
    → (claude_home / "settings.local.json") [pathlib - stdlib]
    → json.loads(file.read_text()) [json - stdlib]
  → self.read_mcp_config() [state_reader.py:61]
    → calls read_settings() + read_settings_local() [see above]
    → (project_dir / ".claude" / "settings.json") [pathlib - stdlib]
    → json.loads(file.read_text()) [json - stdlib]
  → self.read_project_state() [state_reader.py:104]
    → (project_dir / ".claude").exists() [pathlib - stdlib]
    → (project_dir / ".claude" / "settings.json") [pathlib - stdlib]
    → (claude_dir / "rules").glob("*.md") [pathlib - stdlib]
    → (project_dir / "CLAUDE.md").exists() [pathlib - stdlib]
  → self.read_hooks() [state_reader.py:144]
    → calls read_settings() + read_project_state() [see above]
  → self.read_hooks_dir() [state_reader.py:267]
    → (claude_home / "hooks").iterdir() [pathlib - stdlib]
  → self.read_skills_dir() [state_reader.py:233]
    → (claude_home / "skills").iterdir() [pathlib - stdlib]
    → (item / "SKILL.md").exists() etc. [pathlib - stdlib]
  → self.read_global_rules() [state_reader.py:177]
    → (claude_home / "rules").glob("*.md") [pathlib - stdlib]
  → self.read_plugins() [state_reader.py:198]
    → (claude_home / "plugins").iterdir() [pathlib - stdlib]
  → self.read_subagents() [state_reader.py:225]
    → calls read_settings() [see above]
→ cave.paia_states [dict of PAIAState pydantic models]
  → v.model_dump() [pydantic - external]
→ cave.agent_registry [dict of AgentRegistration pydantic models]
  → v.model_dump() [pydantic - external]
→ cave.remote_agents [dict of RemoteAgentHandle pydantic models]
  → v.model_dump() [pydantic - external]
```

### `POST /command` [http_server.py:395]

```
→ cave._ensure_attached() [see above]
→ cave.main_agent.send_keys(command, "Enter") [agent.py:254]
  → subprocess.run(["tmux", "send-keys", "-t", session, command]) [subprocess - stdlib]
  → subprocess.run(["tmux", "send-keys", "-t", session, "Enter"]) [subprocess - stdlib]
```

### `POST /attach` [http_server.py:406]

```
→ (if "session" in data) cave.config.main_agent_session = data["session"] [pydantic field]
→ cave._attach_to_session() [cave_agent.py:109] (see startup)
```

### `GET /inspect` [http_server.py:415]

```
→ cave.inspect() [cave_agent.py:131]
  → cave.paia_states items → v.model_dump() [pydantic - external]
  → cave.agent_registry items → v.model_dump() [pydantic - external]
  → cave.remote_agents items → v.model_dump() [pydantic - external]
  → cave.message_router_summary() [MessageRouterMixin, message_router.py:89]
    → (config.data_dir / "inboxes").iterdir() [pathlib - stdlib]
    → agent_dir.glob("*.json") [pathlib - stdlib]
  → cave.get_hook_status() [HookRouterMixin, hook_router.py:148] (see GET /hooks/status)
  → cave.sse_status() [SSEMixin, sse.py:38]
    → self.event_queue.qsize() [asyncio.Queue - stdlib]
```

---

## 11. INBOX ENDPOINTS

### `GET /messages/inbox/{inbox_id}/count` [http_server.py:421]

```
→ cave.get_inbox(inbox_id) [MessageRouterMixin, message_router.py:53]
  → self._get_inbox_dir(agent_id) [message_router.py:20]
    → (config.data_dir / "inboxes" / agent_id).mkdir() [pathlib - stdlib]
  → inbox_dir.glob("*.json") [pathlib - stdlib]
  → json.loads(file.read_text()) [json/pathlib - stdlib]
```

---

## 12. PAIA STATE ENDPOINTS

### `GET /paias` [http_server.py:429]

```
→ cave.paia_states [dict of PAIAState]
  → v.model_dump() [pydantic - external]
```

### `POST /paias/{paia_id}` [http_server.py:434]

```
→ cave.update_paia_state(paia_id, **data) [PAIAStateMixin, paia_state.py:21]
  → (if new) PAIAState(paia_id=paia_id) [models.py:32, pydantic - external]
  → setattr(state, key, value) [builtins - stdlib]
  → state.last_heartbeat = datetime.utcnow() [datetime - stdlib]
  → self._emit_event("paia_state_changed", ...) [SSEMixin, sse.py:20]
→ state.model_dump() [pydantic - external]
```

---

## 13. REMOTE AGENT ENDPOINTS

### `POST /run_agent` [http_server.py:441]

```
→ await cave.spawn_remote(**request) [RemoteAgentMixin, remote_agent_mixin.py:23]
  → RemoteAgentHandle(agent_id, config, status, spawned_by) [models.py:60, pydantic - external]
  → self._emit_event("remote_agent_spawned", ...) [SSEMixin]
  → (if sdna_enabled):
    → from cave.core.remote_agent import RemoteAgent, RemoteAgentConfig [remote_agent.py]
    → RemoteAgentConfig(name, system_prompt, goal_template, **kwargs) [remote_agent.py:31, dataclass]
    → RemoteAgent(config) [remote_agent.py:55]
      → (checks SDNA_AVAILABLE)
    → await agent.run(inputs) [remote_agent.py:69]
      → (if SDNA not available) returns error
      → HermesConfig(name, system_prompt, ...) [sdna - external]
      → await agent_step(hermes_config, inputs) [sdna - external]
        → (sdna internally runs claude -p subprocess)
      → result.status checks [sdna - external]
  → self._emit_event("remote_agent_completed", ...) [SSEMixin]
```

### `GET /remote_agents` [http_server.py:446]

```
→ cave.remote_agents [dict of RemoteAgentHandle]
  → v.model_dump() [pydantic - external]
```

### `GET /remote_agents/{agent_id}` [http_server.py:451]

```
→ cave.get_remote_status(agent_id) [RemoteAgentMixin, remote_agent_mixin.py:79]
  → self.remote_agents.get(agent_id) [dict - stdlib]
  → handle.model_dump() [pydantic - external]
```

---

## 14. SSE EVENTS ENDPOINT

### `GET /events` [http_server.py:458]

```
→ StreamingResponse(cave.event_generator(), media_type="text/event-stream") [starlette - external]
→ cave.event_generator() [SSEMixin, sse.py:32]
  → async generator:
    → await self.event_queue.get() [asyncio.Queue - stdlib]
    → json.dumps(event) [json - stdlib]
    → yields f"data: {json_str}\n\n" [str - stdlib]
```

---

## 15. HEALTH ENDPOINT

### `GET /health` [http_server.py:342]

```
→ returns {"status": "ok", "version": "0.1.0"} [dict literal - stdlib]
```

---

## 16. DEPENDENCY SUMMARY

### External Packages (Required)

| Package | Used By | Purpose |
|---------|---------|---------|
| **fastapi** | http_server.py | Web framework, route decorators |
| **starlette** | http_server.py | StreamingResponse for SSE |
| **pydantic** | models.py, config.py, agent.py, llegos | BaseModel, Field, validation |
| **httpx** | cave_agent.py | Async HTTP client for heartbeats |
| **llegos** | agent.py | Actor/Message/Object base classes |
| **uvicorn** | http_server.py main() | ASGI server |

### External Packages (Optional, graceful fallback)

| Package | Used By | Purpose |
|---------|---------|---------|
| **sdna** | anatomy.py, remote_agent.py, dna.py | Heartbeat, HeartbeatScheduler, agent_step, HermesConfig, ContextEngineeringLib, ActivateLoop |
| **capability_predictor** | capability_resolver.py | RAG-based capability recommendations |

### llegos Sub-Dependencies (Transitive)

| Package | Used By | Purpose |
|---------|---------|---------|
| **beartype** | llegos.py | Runtime type checking |
| **deepmerge** | llegos.py | Dict merging |
| **ksuid** | llegos.py | K-Sortable unique IDs |
| **networkx** | llegos.py | DiGraph, MultiGraph |
| **pydash** | llegos.py | snake_case utility |
| **pyee** | llegos.py | EventEmitter |
| **sorcery** | llegos.py | delegate_to_attr, maybe |

### Stdlib Modules Used

| Module | Used By | Purpose |
|--------|---------|---------|
| **subprocess** | agent.py, hooks.py, tui.py, cave_agent.py | tmux commands, script execution |
| **asyncio** | sse.py, agent.py | Queue, sleep |
| **json** | config.py, state_reader.py, message_router.py, hooks.py, omnisanc.py, hook_control.py, config_snapshots.py, capability_resolver.py | JSON parse/serialize |
| **pathlib** | config.py, state_reader.py, omnisanc.py, hook_control.py, config_snapshots.py, agent.py, hooks.py, capability_resolver.py, cave_agent.py | Path operations |
| **hashlib** | config_snapshots.py | SHA256 hashing for config comparison |
| **shutil** | config_snapshots.py | File/directory copy/move/delete |
| **importlib** | hooks.py, capability_resolver.py | Dynamic module loading |
| **inspect** | hooks.py | Class member inspection |
| **logging** | Most files | Logger |
| **time** | agent.py, hook_router.py, loop_manager.py | sleep, timestamps |
| **datetime** | paia_state.py, message_router.py, cave_agent.py, config_snapshots.py | Timestamps |
| **re** | state_reader.py | Regex for context % parsing |
| **os** | config.py, hooks.py, capability_resolver.py | Environment variables |
| **uuid** | message_router.py | Message ID generation |
| **collections.deque** | agent.py | Inbox queue |
| **dataclasses** | agent.py, state_reader.py, dna.py, anatomy.py, loops/*.py, remote_agent.py | @dataclass |
| **enum** | agent.py, hooks.py, dna.py | Enum classes |
| **traceback** | agent.py, remote_agent.py, transitions.py | Stack trace formatting |
| **argparse** | http_server.py | CLI arg parsing |

### File-Based State (Read/Write Locations)

| File/Dir | Endpoint(s) | R/W |
|----------|-------------|-----|
| `/tmp/heaven_data/cave_agent_config.json` | startup, POST /hooks/active | R/W |
| `/tmp/heaven_data/config_archives/` | all /configs/* endpoints | R/W |
| `/tmp/heaven_data/cave_hooks/` | startup, POST /hooks/scan | R |
| `/tmp/heaven_data/cave_hooks/scripts.json` | startup | R |
| `/tmp/heaven_data/omnisanc_core/.course_state` | omnisanc endpoints | R |
| `/tmp/heaven_data/omnisanc_core/.omnisanc_disabled` | omnisanc enable/disable | R/W |
| `/tmp/metabrainhook_state.txt` | metabrainhook state | R/W |
| `/tmp/heaven_data/metabrainhook_config.json` | metabrainhook prompt | R/W |
| `/tmp/heaven_data/paia_mode.txt` | PAIA mode | R/W |
| `/tmp/heaven_data/paia_auto.txt` | auto mode | R/W |
| `/tmp/hook_control.json` | GET /hooks/status | R |
| `/tmp/active_promise.md` | autopoiesis exit condition | R |
| `/tmp/heaven_data/inboxes/{agent_id}/` | inbox endpoints | R/W |
| `~/.claude/settings.json` | GET /state | R |
| `~/.claude/settings.local.json` | GET /state | R |
| `~/.claude/rules/` | GET /state | R |
| `~/.claude/hooks/` | GET /state, config archives | R |
| `~/.claude/skills/` | GET /state | R |
| `~/.claude/plugins/` | GET /state | R |

### Subprocess Commands Executed

| Command | From | Purpose |
|---------|------|---------|
| `tmux has-session -t {session}` | agent.py, cave_agent.py | Check session exists |
| `tmux new-session -d -s {session} -c {dir}` | agent.py | Create session |
| `tmux kill-session -t {session}` | agent.py | Kill session |
| `tmux send-keys -t {session} {text} [Enter]` | agent.py, loops/base.py, tui.py | Send input to session |
| `tmux capture-pane -t {session} -p -S -{limit}` | agent.py | Capture pane output |
| `tmux set-option -t {session} display-time {ms}` | tui.py | Set display time |
| `tmux display-message -t {session} {msg}` | tui.py | Status bar message |
| `tmux display-popup -t {session} ...` | tui.py | Popup window |
| `python3 {script_path}` | hooks.py ScriptHookAdapter | Execute hook script |
| `which gum` | tui.py | Check gum availability |
| `gum confirm/choose/input/spin/style ...` | tui.py | Interactive TUI elements |

---

## CLASS HIERARCHY

```
pydantic.BaseModel
  └── llegos.Object (id, metadata)
        ├── llegos.Actor (receive, emit, event handling via pyee.EventEmitter)
        │     ├── llegos.Network (actors graph via networkx.MultiGraph)
        │     ├── cave.core.agent.CodeAgent (inbox via deque, tmux via subprocess)
        │     │     └── cave.core.agent.ClaudeCodeAgent (Claude-specific defaults)
        │     └── (Messages sent between actors)
        └── llegos.Message (sender, receiver, parent, created_at)
              ├── cave.core.agent.InboxMessage (ingress, priority, content)
              │     ├── UserPromptMessage (source_id)
              │     └── SystemEventMessage (event_type, event_data)
              ├── BlockedMessage (reason, context, blocking_question)
              └── CompletedMessage (result, summary)

CAVEAgent(
  PAIAStateMixin,        # paia_states dict ops
  AgentRegistryMixin,    # agent_registry dict ops
  MessageRouterMixin,    # file-based inbox routing (json files in inboxes/ dir)
  HookRouterMixin,       # hook signal processing, HookRegistry, capability resolver
  LoopManagerMixin,      # AgentInferenceLoop lifecycle
  RemoteAgentMixin,      # SDNA remote agent spawning
  SSEMixin,              # Server-Sent Events via asyncio.Queue
  OmnisancMixin,         # Omnisanc state files, metabrainhook state files
  AnatomyMixin,          # Heart (scheduler), Blood (context carrier), Organs
  TUIMixin,              # tmux display: messages, popups, dialogs, menus, spinners
)
  └── Fields: config (CAVEConfig), main_agent (ClaudeCodeAgent), state_reader (ClaudeStateReader),
              config_manager (MainAgentConfigManager), dna (AutoModeDNA)
```

---

*Trace completed. All 30+ endpoints traced through CAVEAgent god object, 10 mixins, 6+ support modules, llegos Actor model, to stdlib/external package terminals.*
