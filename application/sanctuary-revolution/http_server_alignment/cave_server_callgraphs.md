# CAVE HTTP Server — Full Callgraphs

Server file: `/tmp/cave/cave/server/http_server.py`
God object: `/tmp/cave/cave/core/cave_agent.py` → `CAVEAgent`
CAVEAgent inherits from 10 mixins: PAIAStateMixin, AgentRegistryMixin, MessageRouterMixin, HookRouterMixin, LoopManagerMixin, RemoteAgentMixin, SSEMixin, OmnisancMixin, AnatomyMixin, TUIMixin

---

## Startup / Shutdown

### startup (http_server.py:26-30)
```
@app.on_event("startup")
async def startup():
  → global cave
  → cave = CAVEAgent(CAVEConfig.load())
    → CAVEConfig.load() (config.py:76-98)
      → Path(CAVE_AGENT_CONFIG_PATH).exists() [pathlib]
      IF exists:
        → CAVE_AGENT_CONFIG_PATH.read_text() [pathlib.Path.read_text]
        → json.loads() [stdlib json]
        → cls.model_validate(data) [pydantic BaseModel]
        IF config.restart_config:
          → archive_path = CAVE_CONFIG_ARCHIVES_DIR / f"{config.restart_config}.json"
          → archive_path.exists() [pathlib]
          → json.loads(archive_path.read_text()) [stdlib]
          → cls.model_validate(archive_data) [pydantic]
      ELSE:
        → cls() [pydantic default construction]
        → config.save() (config.py:63-66)
          → CAVE_AGENT_CONFIG_PATH.parent.mkdir() [pathlib]
          → CAVE_AGENT_CONFIG_PATH.write_text(self.model_dump_json()) [pathlib + pydantic]
    → CAVEAgent.__init__(config) (cave_agent.py:48-89)
      → self.config = config
      → self.paia_states = {}
      → self.agent_registry = {}
      → self.remote_agents = {}
      → self.state_reader = ClaudeStateReader(project_dir=...) (state_reader.py:22-35)
        → Path(self.claude_home) [pathlib]
        → Path(self.project_dir) [pathlib]
      → self._attach_to_session() (cave_agent.py:109-124) [see below]
      → self._init_hook_router() [from HookRouterMixin] (hook_router.py:27-35)
        → HookRegistry(self.config.hook_dir) (hooks.py:174-180)
        → self.hook_registry.scan() (hooks.py:182-228)
          → self.hooks_dir.glob("*.py") [pathlib]
          FOR each .py file:
            → self._load_entry(py_file) (hooks.py:230-283)
              → importlib.util.spec_from_file_location() [stdlib importlib]
              → importlib.util.module_from_spec() [stdlib]
              → spec.loader.exec_module(module) [stdlib]
              → inspect.getmembers(module) [stdlib inspect]
          → self.load_scripts_config() (hooks.py:392-426)
            → self._scripts_config_path.exists() [pathlib]
            IF exists:
              → json.loads(self._scripts_config_path.read_text()) [stdlib]
              FOR each entry:
                → self.register_script(name, hook_type, path) (hooks.py:338-370)
                  → Path(path).exists() [pathlib]
                  → ScriptHookAdapter(name, hook_type_lower, script_path)
        → self.hook_registry.load_scripts_config() [same as above, called again]
        → self._hook_state = {}
        → self._hook_history = []
      → self._init_loop_manager() [from LoopManagerMixin] (loop_manager.py:27-35)
        → self._loop_state = {...}
        → self._active_loop = None
      → self._init_sse() [from SSEMixin] (sse.py:16-18)
        → self.event_queue = asyncio.Queue(maxsize=1000) [stdlib asyncio]
      → self._init_omnisanc() [from OmnisancMixin] (omnisanc.py:25-29)
        → OMNISANC_STATE_FILE.parent.mkdir() [pathlib]
        → METABRAINHOOK_PROMPT_FILE.parent.mkdir() [pathlib]
      → self._init_anatomy() [from AnatomyMixin] (anatomy.py:181-187)
        → self.organs = {}
        → self.heart = Heart(name="main_heart") (anatomy.py:47-68)
          IF SDNA_AVAILABLE:
            → HeartbeatScheduler() [sdna external]
        → self.blood = Blood() (anatomy.py:116-128)
        → self.organs["heart"] = self.heart
      → self.dna = None
      IF config.system_prompt_template_path and config.system_prompt_target_path:
        → self._render_system_prompt() (cave_agent.py:99-107)
          → self.config.system_prompt_template_path.read_text() [pathlib]
          → str.replace() for each template var [stdlib]
          → self.config.system_prompt_target_path.parent.mkdir() [pathlib]
          → self.config.system_prompt_target_path.write_text(rendered) [pathlib]
      → self.config.data_dir.mkdir() [pathlib]
      → self.config.hook_dir.mkdir() [pathlib]
      → self.config_manager = MainAgentConfigManager(data_dir=..., claude_home=...)
        (config_snapshots.py:22-48)
        → self.archives_dir = data_dir / "config_archives"
        → self.active_file = data_dir / "config_archives" / "active.json"
        → self.archives_dir.mkdir() [pathlib]
```

### shutdown (http_server.py:33-35)
```
@app.on_event("shutdown")
async def shutdown():
  → pass  # No-op
```

---

## Config Archives Endpoints

### GET /configs (http_server.py:39-42)
```
Handler: list_configs (http_server.py:40)
  → cave.list_config_archives() (cave_agent.py:193-195) [direct method on CAVEAgent]
    → self.config_manager.list_archives() (config_snapshots.py:209-231)
      → self.archives_dir.iterdir() [pathlib]
      FOR each archive_dir:
        → (archive_dir / "_metadata.json").exists() [pathlib]
        IF exists:
          → json.loads(metadata_file.read_text()) [stdlib]
      → archives.sort() [list.sort]
      → self._get_active_config() (config_snapshots.py:233-238)
        → self.active_file.exists() [pathlib]
        IF exists:
          → json.loads(self.active_file.read_text()) [stdlib]
```

### GET /configs/active (http_server.py:45-48)
```
Handler: get_active_config (http_server.py:46)
  → cave.get_active_config() (cave_agent.py:197-199) [direct method on CAVEAgent]
    → self.config_manager.get_active_info() (config_snapshots.py:240-263)
      → self._detect_matching_archive() (config_snapshots.py:77-87)
        → self._compute_config_hash(self.claude_home) (config_snapshots.py:54-75)
          FOR each rel_path in self.config_files:
            → (base_path / rel_path).exists() [pathlib]
            → file_path.read_bytes() [pathlib]
            → hashlib.sha256().update() [stdlib hashlib]
          FOR each rel_path in self.config_dirs:
            → dir_path.exists() [pathlib]
            → dir_path.rglob("*") [pathlib]
            → file.read_bytes() [pathlib]
        FOR each archive_dir in self.archives_dir.iterdir():
          → self._compute_config_hash(archive_dir) [same as above]
      IF no match:
        → self.active_file.exists() [pathlib]
        IF exists:
          → json.loads(self.active_file.read_text()) [stdlib]
```

### POST /configs/archive (http_server.py:51-57)
```
Handler: archive_config (http_server.py:52)
  → data.get("name", "")
  IF not name: return {"error": "name required"}
  → cave.archive_config(name) (cave_agent.py:179-184)
    → self.config_manager.archive(name) (config_snapshots.py:89-146)
      → self._get_archive_path(name) (config_snapshots.py:50-52)
        → self.archives_dir / name [pathlib]
      IF archive_path.exists(): return error
      → archive_path.mkdir() [pathlib]
      FOR each rel_path in self.config_files:
        → src = self.claude_home / rel_path [pathlib]
        IF src.exists():
          → dst.parent.mkdir() [pathlib]
          → shutil.copy2(src, dst) [stdlib shutil]
      FOR each rel_path in self.config_dirs:
        → src = self.claude_home / rel_path [pathlib]
        IF src.exists() and src.is_dir():
          → shutil.copytree(src, dst, dirs_exist_ok=True) [stdlib shutil]
      → (archive_path / "_metadata.json").write_text(json.dumps(metadata)) [pathlib + stdlib]
    IF "error" not in result:
      → self._emit_event("config_archived", {"name": name}) [from SSEMixin] (sse.py:20-30)
        → self.event_queue.put_nowait(event) [asyncio.Queue]
```

### POST /configs/inject (http_server.py:60-66)
```
Handler: inject_config (http_server.py:61)
  → data.get("name", "")
  IF not name: return {"error": "name required"}
  → cave.inject_config(name) (cave_agent.py:186-191)
    → self.config_manager.inject(name) (config_snapshots.py:148-207)
      → self._get_archive_path(name) (config_snapshots.py:50-52)
      IF not archive_path.exists(): return error
      → self.archive(backup_name) [recursive call to archive above]
      FOR each rel_path in self.config_files:
        → src = archive_path / rel_path [pathlib]
        IF src.exists():
          → shutil.copy2(src, dst) [stdlib shutil]
      FOR each rel_path in self.config_dirs:
        → src = archive_path / rel_path [pathlib]
        IF src.exists() and src.is_dir():
          IF dst.exists(): → shutil.rmtree(dst) [stdlib shutil]
          → shutil.copytree(src, dst) [stdlib shutil]
      → self.active_file.write_text(json.dumps(active_info)) [pathlib + stdlib]
    IF "error" not in result:
      → self._emit_event("config_injected", {...}) [from SSEMixin]
```

### DELETE /configs/{name} (http_server.py:69-72)
```
Handler: delete_config (http_server.py:70)
  → cave.delete_config_archive(name) (cave_agent.py:201-203)
    → self.config_manager.delete_archive(name) (config_snapshots.py:265-272)
      → self._get_archive_path(name) (config_snapshots.py:50-52)
      IF not exists: return error
      → shutil.rmtree(archive_path) [stdlib shutil]
```

### POST /configs/export (http_server.py:75-82)
```
Handler: export_config (http_server.py:76)
  → data.get("name", ""), data.get("dest_path", "")
  IF not name or not dest_path: return error
  → cave.export_config_archive(name, dest_path) (cave_agent.py:205-207)
    → self.config_manager.export_archive(name, dest_path) (config_snapshots.py:274-285)
      → self._get_archive_path(name)
      IF not exists: return error
      → Path(dest_path)
      IF dest.exists(): return error
      → shutil.copytree(archive_path, dest) [stdlib shutil]
```

### POST /configs/import (http_server.py:85-92)
```
Handler: import_config (http_server.py:86)
  → data.get("source_path", ""), data.get("name", "")
  IF not source_path or not name: return error
  → cave.import_config_archive(source_path, name) (cave_agent.py:209-211)
    → self.config_manager.import_archive(source_path, name) (config_snapshots.py:287-298)
      → Path(source_path)
      IF not source.exists(): return error
      → self._get_archive_path(name)
      IF archive_path.exists(): return error
      → shutil.copytree(source, archive_path) [stdlib shutil]
```

---

## Loop Manager Endpoints

### GET /loops/state (http_server.py:96-99)
```
Handler: get_loop_state (http_server.py:97)
  → cave.get_loop_state() [from LoopManagerMixin] (loop_manager.py:37-47)
    → returns self._loop_state merged with:
      → list(AVAILABLE_LOOPS.keys()) [from loops/__init__.py]
      IF self._active_loop:
        → self._active_loop.name, .description, .active_hooks [AgentInferenceLoop attrs]
```

### POST /loops/start (http_server.py:102-107)
```
Handler: start_loop (http_server.py:103)
  → data.get("loop", "autopoiesis")
  → data.get("config")
  → cave.start_loop(loop_type, config) [from LoopManagerMixin] (loop_manager.py:49-93)
    IF self._active_loop:
      → self.stop_loop() [see below]
    IF loop_type not in AVAILABLE_LOOPS: return error
    → loop = AVAILABLE_LOOPS[loop_type]
    → self._active_loop = loop
    → self._loop_state = {...}
    → loop.activate(self) [AgentInferenceLoop] (loops/base.py:60-87)
      → cave_agent.config.main_agent_config.active_hooks = self.active_hooks.copy()
      IF self.prompt and cave_agent.main_agent:
        → cave_agent.main_agent.send_keys(self.prompt, 0.5, "Enter")
          [CodeAgent.send_keys] (agent.py:254-263)
          → time.sleep(0.5) [stdlib]
          → self._run_tmux("send-keys", "-t", session, prompt) (agent.py:216-219)
            → subprocess.run(["tmux", "send-keys", ...]) [stdlib subprocess]
          → self._run_tmux("send-keys", "-t", session, "Enter")
      IF self.on_start:
        → self.on_start(cave_agent._hook_state) [user-defined callback]
    → self._hook_state["_loop_config"] = config
    IF loop.on_start:
      → loop.on_start(self._hook_state) [called again — redundant with activate]
```

### POST /loops/stop (http_server.py:110-113)
```
Handler: stop_loop (http_server.py:111)
  → cave.stop_loop() [from LoopManagerMixin] (loop_manager.py:95-126)
    IF not self._active_loop: return error
    IF loop.on_stop:
      → loop.on_stop(self._hook_state) [user-defined callback]
    → loop.deactivate(self) [AgentInferenceLoop] (loops/base.py:89-108)
      → cave_agent.config.main_agent_config.active_hooks = {} [clears hooks]
      IF self.on_stop:
        → self.on_stop(cave_agent._hook_state) [user-defined callback]
    → self._active_loop = None
    → self._loop_state = {idle state}
```

### POST /loops/trigger (http_server.py:116-120)
```
Handler: trigger_transition (http_server.py:117)
  → data.get("event", "continue")
  → data.get("data")
  → cave.trigger_transition(event, data) [from LoopManagerMixin] (loop_manager.py:128-162)
    IF not self._active_loop: return error
    → previous_mode = self._loop_state.get("mode")
    FOR condition_name, condition_fn in self._active_loop.conditions.items():
      *** NOTE: AgentInferenceLoop has NO `conditions` attribute (loops/base.py).
      *** This will raise AttributeError at runtime. ***
    → transitions dict lookup
    → self._loop_state updates
```

### POST /loops/pause (http_server.py:123-126)
```
Handler: pause_loop (http_server.py:124)
  → cave.pause_loop() [from LoopManagerMixin] (loop_manager.py:164-172)
    IF not self._active_loop: return error
    → self._hook_state.setdefault(self._active_loop.name, {})["paused"] = True
    → self._loop_state["mode"] = "paused"
```

### POST /loops/resume (http_server.py:129-132)
```
Handler: resume_loop (http_server.py:130)
  → cave.resume_loop() [from LoopManagerMixin] (loop_manager.py:174-182)
    IF not self._active_loop: return error
    → self._hook_state.setdefault(self._active_loop.name, {})["paused"] = False
    → self._loop_state["mode"] = "working"
```

### GET /loops/available (http_server.py:135-138)
```
Handler: list_available_loops (http_server.py:136)
  → cave.list_available_loops() [from LoopManagerMixin] (loop_manager.py:184-193)
    FOR name, loop in AVAILABLE_LOOPS.items():
      → loop.description, loop.active_hooks
      → list(loop.conditions.keys())
        *** Same bug: `conditions` not an attribute of AgentInferenceLoop ***
```

---

## DNA (Auto Mode) Endpoints

### GET /dna/status (http_server.py:142-145)
```
Handler: get_dna_status (http_server.py:143)
  → cave.get_dna_status() (cave_agent.py:234-238)
    IF not self.dna: return {"status": "no_dna"}
    → self.dna.get_status() [AutoModeDNA] (dna.py:208-218)
      → self.current_loop.name if self.current_loop else None
      → [l.name for l in self.loops]
```

### POST /dna/start (http_server.py:148-162)
```
Handler: start_auto_mode (http_server.py:149)
  → from ..core.dna import create_dna [lazy import]
  → data.get("loop_names", ["autopoiesis"])
  → data.get("exit_behavior", "cycle")
  → data.get("name", "auto")
  → dna = create_dna(name=name, loop_names=loop_names, exit_behavior=exit_behavior)
    (dna.py:221-244)
    FOR loop_name in loop_names:
      IF loop_name in AVAILABLE_LOOPS:
        → loops.append(AVAILABLE_LOOPS[loop_name])
    → AutoModeDNA(name=name, loops=loops, exit_behavior=ExitBehavior(exit_behavior))
  → cave.start_auto_mode(dna) (cave_agent.py:215-218)
    → self.dna = dna
    → self.dna.start(self) [AutoModeDNA] (dna.py:58-76)
      IF not self.loops: return error
      → self.current_index = 0
      → self.active = True
      → loop = self.current_loop [property] (dna.py:52-56)
      → loop.activate(cave_agent) [AgentInferenceLoop.activate] (loops/base.py:60-87)
        [see POST /loops/start for full chain]
```

### POST /dna/stop (http_server.py:165-168)
```
Handler: stop_auto_mode (http_server.py:166)
  → cave.stop_auto_mode() (cave_agent.py:220-225)
    IF not self.dna: return error
    → self.dna.stop(self) [AutoModeDNA] (dna.py:78-91)
      → loop = self.current_loop [property]
      IF loop:
        → loop.deactivate(cave_agent) [AgentInferenceLoop.deactivate] (loops/base.py:89-108)
      → self.active = False
    → self.dna = None
```

---

## Module Endpoints

### GET /modules (http_server.py:172-175)
```
Handler: list_modules (http_server.py:173)
  → cave.list_modules()
    *** NOT DEFINED on CAVEAgent or any mixin ***
    *** Will raise AttributeError at runtime ***
```

### POST /modules/load (http_server.py:178-185)
```
Handler: load_module (http_server.py:179)
  → cave.load_module(name, code)
    *** NOT DEFINED on CAVEAgent or any mixin ***
    *** Will raise AttributeError at runtime ***
```

### POST /modules/unload (http_server.py:188-194)
```
Handler: unload_module (http_server.py:189)
  → cave.unload_module(name)
    *** NOT DEFINED on CAVEAgent or any mixin ***
    *** Will raise AttributeError at runtime ***
```

### GET /modules/history (http_server.py:197-200)
```
Handler: get_module_history (http_server.py:198)
  → cave.get_module_history()
    *** NOT DEFINED on CAVEAgent or any mixin ***
    *** Will raise AttributeError at runtime ***
```

---

## Hook Signal Endpoints

### POST /hook/{hook_type} (http_server.py:204-214)
```
Handler: handle_hook_signal (http_server.py:205)
  → cave.run_omnisanc() (cave_agent.py:242-306) [direct method on CAVEAgent]
    → self.is_omnisanc_enabled() [from OmnisancMixin] (omnisanc.py:92-97)
      → OMNISANC_DISABLED_FILE.exists() [pathlib]
    IF disabled: return {"status": "disabled"}
    → self.get_omnisanc_state() [from OmnisancMixin] (omnisanc.py:35-55)
      → OMNISANC_STATE_FILE.exists() [pathlib]
      IF exists: → json.loads(OMNISANC_STATE_FILE.read_text()) [stdlib]
    → self.get_paia_mode() (cave_agent.py:308-321) [direct method on CAVEAgent]
      → Path("/tmp/heaven_data/paia_mode.txt")
      IF exists: → mode_file.read_text().strip().upper() [pathlib + str]
    → self.get_auto_mode() (cave_agent.py:323-336) [direct method on CAVEAgent]
      → Path("/tmp/heaven_data/paia_auto.txt")
      IF exists: → auto_file.read_text().strip().upper() [pathlib + str]
    → Zone logic (if/elif chain based on state dict flags)
    → self.config.main_agent_config.active_hooks = {...}
  → cave.handle_hook(hook_type, data) [from HookRouterMixin] (hook_router.py:37-126)
    → source = payload.pop("source", "claude_code")
    IF source == "openclaw":
      → self._normalize_openclaw_payload(hook_type, payload) (hook_router.py:159-207)
        → payload.copy() [dict]
        → field mapping based on hook_type_lower
    → hook_type_lower = hook_type.lower() [str]
    → active_hook_names = self.config.main_agent_config.active_hooks.get(hook_type_lower, [])
    IF not active_hook_names: return continue
    → event = {..., "ts": time.time()} [stdlib time]
    → self._hook_history.append(event)
    IF len > 100: trim [list slicing]
    → all_hooks = self.hook_registry.get_hooks_for_type(hook_type_lower) (hooks.py:285-316)
      FOR each entry in self._registry.values():
        IF entry.hook_type matches and entry.hook_class not None:
          IF entry.instance is None:
            → entry.hook_class() [instantiate hook class]
          → matching.append(entry.instance)
      FOR each adapter in self._scripts.values():
        IF adapter.hook_type matches:
          → matching.append(adapter)
    → hooks = [h for h in all_hooks if h.name in active_hook_names] [list comprehension]
    → get_capability_context_for_hook(hook_type_lower, payload, enabled=rag_enabled)
      (capability_resolver.py:98-124)
      IF not enabled or hook_type not in ("pretooluse", "stop"): return None
      → extract_query_from_hook_payload(payload) (capability_resolver.py:70-95)
        → Checks tool_name, returns query string or None
      IF not query: return None
      → resolve_capabilities(query, compact=True) (capability_resolver.py:48-67)
        → _get_rag_module() (capability_resolver.py:18-45)
          TRY: → from capability_predictor import unified_rag [external import]
          EXCEPT: → importlib.util.spec_from_file_location() + exec_module() [stdlib]
        IF rag is None: return None
        → rag.get_capability_context(query, compact=compact) [external module call]
    FOR each hook in hooks:
      → hook(payload, self._hook_state) [ClaudeCodeHook.__call__] (hooks.py:83-86)
        → self.handle(payload, state) [abstract — subclass impl]
        → result.to_dict() (hooks.py:38-45)
      OR for ScriptHookAdapter: (hooks.py:110-138)
        → subprocess.run(["python3", str(self.script_path)], input=json.dumps(payload), ...)
          [stdlib subprocess — spawns external process]
        → json.loads(result.stdout) [stdlib]
      IF result.get("decision") == "block": return block response
    → self.check_dna_transition() (cave_agent.py:228-232) [direct method]
      IF not self.dna or not self.dna.active: return {"status": "no_dna"}
      → self.dna.check_and_transition(self) [AutoModeDNA] (dna.py:93-199)
        → loop.check_exit(state) [AgentInferenceLoop] (loops/base.py:110-118)
          → self.exit_condition(state) [user-defined callback or None]
        IF exit condition met:
          → loop.deactivate(cave_agent) [see above]
          → Handle next (string loop name or TransitionAction chain)
          IF TransitionAction:
            → from sdna import ContextEngineeringLib, ActivateLoop [external]
            → next_target.execute_chain(lib) [sdna TransitionAction]
          → next_loop.activate(cave_agent) [see above]
    → Build response dict with additionalContext
```

### POST /hooks/scan (http_server.py:217-220)
```
Handler: scan_hooks (http_server.py:218)
  → cave.scan_hooks() [from HookRouterMixin] (hook_router.py:128-130)
    → self.hook_registry.scan() (hooks.py:182-228)
      [see startup chain for full scan details]
```

### GET /hooks (http_server.py:223-226)
```
Handler: list_hooks (http_server.py:224)
  → cave.list_hooks() [from HookRouterMixin] (hook_router.py:132-134)
    → self.hook_registry.list() (hooks.py:318-332)
      → dict comprehension over self._registry
```

### GET /hooks/status (http_server.py:229-232)
```
Handler: get_hooks_status (http_server.py:230)
  → cave.get_hook_status() [from HookRouterMixin] (hook_router.py:148-157)
    → from ..hook_control import HookControl [lazy import]
    → self.hook_registry.list() (hooks.py:318-332)
    → HookControl.get_all() (hook_control.py:73-76)
      → HookControl._load() (hook_control.py:34-38)
        → HOOK_CONTROL_CONFIG.exists() [pathlib]
        IF exists: → json.loads(HOOK_CONTROL_CONFIG.read_text()) [stdlib]
    → list(self._hook_state.keys())
    → len(self._hook_history)
```

### GET /hooks/active (http_server.py:235-238)
```
Handler: get_active_hooks (http_server.py:236)
  → cave.config.main_agent_config.active_hooks [direct attribute access]
    → MainAgentConfig.active_hooks (models.py:21) [Dict[str, List[str]]]
```

### POST /hooks/active (http_server.py:241-247)
```
Handler: set_active_hooks (http_server.py:242)
  → cave.config.main_agent_config.active_hooks = data [direct assignment]
  → cave.config.save() (config.py:63-66)
    → CAVE_AGENT_CONFIG_PATH.parent.mkdir() [pathlib]
    → CAVE_AGENT_CONFIG_PATH.write_text(self.model_dump_json()) [pathlib + pydantic]
  → cave.scan_hooks() [from HookRouterMixin] (hook_router.py:128-130)
    → self.hook_registry.scan() [see above]
  → returns {"active_hooks": ...}
```

---

## Omnisanc Endpoints

### GET /omnisanc/state (http_server.py:251-254)
```
Handler: get_omnisanc_state (http_server.py:252)
  → cave.get_omnisanc_state() [from OmnisancMixin] (omnisanc.py:35-55)
    → OMNISANC_STATE_FILE.exists() [pathlib]
    IF exists: → json.loads(OMNISANC_STATE_FILE.read_text()) [pathlib + stdlib]
    ELSE: return {}
```

### GET /omnisanc/status (http_server.py:257-260)
```
Handler: get_omnisanc_status (http_server.py:258)
  → cave.get_omnisanc_status() [from OmnisancMixin] (omnisanc.py:219-236)
    → self.is_omnisanc_enabled() (omnisanc.py:92-97)
      → OMNISANC_DISABLED_FILE.exists() [pathlib]
    → self.get_omnisanc_zone() (omnisanc.py:57-78)
      → self.get_omnisanc_state() [reads file — see above]
      → Zone logic (if/elif chain on state flags)
    → self.is_home() (omnisanc.py:80-82)
      → self.get_omnisanc_state() [reads file again]
    → state.get(...) for course_plotted, mission_active, mission_id, domain, subdomain
    → self.get_metabrainhook_state() (omnisanc.py:141-148)
      → METABRAINHOOK_STATE_FILE.exists() [pathlib]
      IF exists: → METABRAINHOOK_STATE_FILE.read_text().strip().lower() [pathlib + str]
    → METABRAINHOOK_PROMPT_FILE.exists() [pathlib]
```

### GET /omnisanc/zone (http_server.py:263-266)
```
Handler: get_omnisanc_zone (http_server.py:264)
  → cave.get_omnisanc_zone() [from OmnisancMixin] (omnisanc.py:57-78)
    → self.get_omnisanc_state() [reads OMNISANC_STATE_FILE — see above]
    → Zone logic returns "HOME"/"STARPORT"/"LAUNCH"/"SESSION"/"LANDING"/"MISSION"
```

### GET /omnisanc/enabled (http_server.py:269-272)
```
Handler: is_omnisanc_enabled (http_server.py:270)
  → cave.is_omnisanc_enabled() [from OmnisancMixin] (omnisanc.py:92-97)
    → not OMNISANC_DISABLED_FILE.exists() [pathlib]
```

### POST /omnisanc/enable (http_server.py:275-278)
```
Handler: enable_omnisanc (http_server.py:276)
  → cave.enable_omnisanc() [from OmnisancMixin] (omnisanc.py:99-116)
    → self.is_omnisanc_enabled() [see above]
    IF OMNISANC_DISABLED_FILE.exists():
      → OMNISANC_DISABLED_FILE.unlink() [pathlib — deletes file]
```

### POST /omnisanc/disable (http_server.py:281-284)
```
Handler: disable_omnisanc (http_server.py:282)
  → cave.disable_omnisanc() [from OmnisancMixin] (omnisanc.py:118-135)
    → self.is_omnisanc_enabled() [see above]
    → OMNISANC_DISABLED_FILE.parent.mkdir() [pathlib]
    → OMNISANC_DISABLED_FILE.write_text("disabled") [pathlib — creates file]
```

---

## Metabrainhook Endpoints

### GET /metabrainhook/state (http_server.py:287-290)
```
Handler: get_metabrainhook_state (http_server.py:288)
  → cave.get_metabrainhook_state() [from OmnisancMixin] (omnisanc.py:141-148)
    → METABRAINHOOK_STATE_FILE.exists() [pathlib]
    IF exists: → METABRAINHOOK_STATE_FILE.read_text().strip().lower() == "on" [pathlib + str]
```

### POST /metabrainhook/state (http_server.py:293-297)
```
Handler: set_metabrainhook_state (http_server.py:294)
  → data.get("on", data.get("enabled", False))
  → cave.set_metabrainhook_state(on) [from OmnisancMixin] (omnisanc.py:150-173)
    → self.get_metabrainhook_state() [see above]
    → METABRAINHOOK_STATE_FILE.write_text("on" if on else "off") [pathlib]
```

### GET /metabrainhook/prompt (http_server.py:300-304)
```
Handler: get_metabrainhook_prompt (http_server.py:301)
  → cave.get_metabrainhook_prompt() [from OmnisancMixin] (omnisanc.py:179-189)
    → METABRAINHOOK_PROMPT_FILE.exists() [pathlib]
    IF exists: → METABRAINHOOK_PROMPT_FILE.read_text() [pathlib]
    ELSE: return None
  → return {"content": content, "exists": content is not None}
```

### POST /metabrainhook/prompt (http_server.py:307-311)
```
Handler: set_metabrainhook_prompt (http_server.py:308)
  → data.get("content", "")
  → cave.set_metabrainhook_prompt(content) [from OmnisancMixin] (omnisanc.py:191-213)
    → METABRAINHOOK_PROMPT_FILE.parent.mkdir() [pathlib]
    → METABRAINHOOK_PROMPT_FILE.write_text(content) [pathlib]
```

---

## PAIA Mode Control Endpoints

### GET /paia/mode (http_server.py:316-322)
```
Handler: get_paia_mode (http_server.py:317)
  → cave.get_paia_mode() (cave_agent.py:308-321) [direct method on CAVEAgent]
    → Path("/tmp/heaven_data/paia_mode.txt")
    → mode_file.exists() [pathlib]
    IF exists: → mode_file.read_text().strip().upper() [pathlib + str]
    ELSE: return "DAY"
  → cave.get_auto_mode() (cave_agent.py:323-336) [direct method on CAVEAgent]
    → Path("/tmp/heaven_data/paia_auto.txt")
    → auto_file.exists() [pathlib]
    IF exists: → auto_file.read_text().strip().upper() [pathlib + str]
    ELSE: return "MANUAL"
```

### POST /paia/mode (http_server.py:325-329)
```
Handler: set_paia_mode (http_server.py:326)
  → data.get("mode", "DAY")
  → cave.set_paia_mode(mode) (cave_agent.py:349-358) [direct method on CAVEAgent]
    → Path("/tmp/heaven_data/paia_mode.txt")
    → mode.upper() [str]
    IF mode not in ("DAY", "NIGHT"): return error
    → mode_file.parent.mkdir() [pathlib]
    → mode_file.write_text(mode) [pathlib]
```

### POST /paia/auto (http_server.py:332-337)
```
Handler: set_auto_mode (http_server.py:333)
  → data.get("mode", "MANUAL")
  → cave.set_auto_mode(mode) (cave_agent.py:338-347) [direct method on CAVEAgent]
    → Path("/tmp/heaven_data/paia_auto.txt")
    → mode.upper() [str]
    IF mode not in ("AUTO", "MANUAL"): return error
    → auto_file.parent.mkdir() [pathlib]
    → auto_file.write_text(mode) [pathlib]
```

---

## Health

### GET /health (http_server.py:340-342)
```
Handler: health (http_server.py:341)
  → return {"status": "ok", "version": "0.1.0"} [pure dict, no calls]
```

---

## Live Mirror Endpoints

### GET /output (http_server.py:346-352)
```
Handler: get_output (http_server.py:347)
  → cave._ensure_attached() (cave_agent.py:126-129) [direct method on CAVEAgent]
    IF self.main_agent and self.main_agent.session_exists():
      → self.main_agent.session_exists() [CodeAgent] (agent.py:221-224)
        → self._run_tmux("has-session", "-t", session) (agent.py:216-219)
          → subprocess.run(["tmux", "has-session", "-t", ...]) [stdlib subprocess]
      return True
    ELSE:
      → self._attach_to_session() (cave_agent.py:109-124) [see startup]
  IF not attached:
    → return {"error": "not attached", "session": cave.config.main_agent_session}
      *** BUG: main_agent_session is NOT a field on CAVEConfig ***
      *** Correct path: cave.config.main_agent_config.tmux_session ***
      *** Will raise AttributeError ***
  → cave.main_agent.capture_pane(history_limit=lines) [CodeAgent] (agent.py:265-271)
    → self._run_tmux("capture-pane", "-t", session, "-p", "-S", f"-{history_limit}")
      → subprocess.run(["tmux", "capture-pane", ...]) [stdlib subprocess]
  → ClaudeStateReader.parse_context_pct(output) [static method] (state_reader.py:316-334)
    → re.search(pattern, pane_output, re.IGNORECASE) [stdlib re]
```

### POST /input (http_server.py:355-365)
```
Handler: send_input (http_server.py:356)
  → cave._ensure_attached() [see above]
  IF not attached: return error (*** same main_agent_session bug ***)
  → data.get("text", ""), data.get("press_enter", True)
  IF press_enter:
    → cave.main_agent.send_keys(text, "Enter") [CodeAgent] (agent.py:254-263)
      → self._run_tmux("send-keys", "-t", session, text) (agent.py:216-219)
        → subprocess.run(["tmux", "send-keys", "-t", ..., text]) [stdlib subprocess]
      → self._run_tmux("send-keys", "-t", session, "Enter")
        → subprocess.run(["tmux", "send-keys", "-t", ..., "Enter"]) [stdlib subprocess]
  ELSE:
    → cave.main_agent.send_keys(text) [same chain, no Enter]
```

### GET /state (http_server.py:368-391)
```
Handler: get_live_state (http_server.py:369)
  → cave._ensure_attached() [see above]
  IF attached:
    → cave.main_agent.capture_pane(lines=50) [CodeAgent]
      *** NOTE: capture_pane has param `history_limit`, not `lines` ***
      *** This passes 50 as positional arg to history_limit, which works ***
      → subprocess.run(["tmux", "capture-pane", ...]) [stdlib subprocess]
    → ClaudeStateReader.parse_context_pct(output) [static] (state_reader.py:316-334)
    → terminal_state dict built
  ELSE:
    → terminal_state = {"attached": False, "session": cave.config.main_agent_session}
      *** same main_agent_session bug ***
  → cave.state_reader.get_complete_state() [ClaudeStateReader] (state_reader.py:291-311)
    → self.read_settings() (state_reader.py:39-47)
      → (self.claude_home / "settings.json").exists() [pathlib]
      IF exists: → json.loads(settings_path.read_text()) [stdlib]
    → self.read_settings_local() (state_reader.py:49-57)
      → (self.claude_home / "settings.local.json").exists() [pathlib]
      IF exists: → json.loads() [stdlib]
    → self.read_mcp_config() (state_reader.py:61-100)
      → self.read_settings() [re-reads]
      → self.read_settings_local() [re-reads]
      → (self.project_dir / ".claude" / "settings.json") read [pathlib + json]
    → self.read_project_state() (state_reader.py:104-140)
      → (self.project_dir / ".claude").exists() [pathlib]
      → settings.json, rules/ glob, CLAUDE.md check [pathlib]
    → self.read_hooks() (state_reader.py:144-173)
      → self.read_settings() [re-reads]
      → self.read_project_state() [re-reads]
    → self.read_hooks_dir() (state_reader.py:267-287)
      → (self.claude_home / "hooks").exists() [pathlib]
      → iterdir, filter .py files [pathlib]
    → self.read_skills_dir() (state_reader.py:233-263)
      → (self.claude_home / "skills").exists() [pathlib]
      → iterdir, check SKILL.md/reference.md/scripts/templates [pathlib]
    → self.read_global_rules() (state_reader.py:177-182)
      → (self.claude_home / "rules").glob("*.md") [pathlib]
    → self.read_plugins() (state_reader.py:198-221)
      → (self.claude_home / "plugins").exists() [pathlib]
      → iterdir [pathlib]
    → self.read_subagents() (state_reader.py:225-229)
      → self.read_settings() [re-reads]
  → cave.paia_states dict → model_dump() [pydantic]
  → cave.agent_registry dict → model_dump() [pydantic]
  → cave.remote_agents dict → model_dump() [pydantic]
```

### POST /command (http_server.py:394-402)
```
Handler: send_command (http_server.py:395)
  → cave._ensure_attached() [see above]
  IF not attached: return error (*** main_agent_session bug ***)
  → data.get("command", "")
  IF not command.startswith("/"): prepend "/"
  → cave.main_agent.send_keys(command, "Enter") [CodeAgent] (agent.py:254-263)
    → subprocess.run(["tmux", "send-keys", ...]) [stdlib subprocess] × 2
```

### POST /attach (http_server.py:405-411)
```
Handler: attach_session (http_server.py:406)
  → data = data or {}
  IF "session" in data:
    → cave.config.main_agent_session = data["session"]
      *** BUG: main_agent_session is NOT a field on CAVEConfig ***
      *** This will SET a new attribute dynamically (pydantic allows extra if configured) ***
      *** Does NOT update cave.config.main_agent_config.tmux_session ***
  → cave._attach_to_session() (cave_agent.py:109-124)
    → session = self.config.main_agent_config.tmux_session [reads correct field]
    → subprocess.run(["tmux", "has-session", "-t", session]) [stdlib subprocess]
    IF session exists:
      → ClaudeCodeAgentConfig(agent_command=..., tmux_session=session, working_directory=...)
      → self.main_agent = ClaudeCodeAgent(config=agent_config)
      → self._emit_event("attached", {"session": session}) [from SSEMixin]
    ELSE:
      → self.main_agent = None
      → self._emit_event("no_session", {"session": session}) [from SSEMixin]
  → return {"attached": success, "session": cave.config.main_agent_session}
    *** same main_agent_session bug ***
```

### GET /inspect (http_server.py:414-416)
```
Handler: inspect (http_server.py:415)
  → cave.inspect() (cave_agent.py:131-146)
    → {k: v.model_dump() for k, v in self.paia_states.items()} [pydantic]
    → {k: v.model_dump() for k, v in self.agent_registry.items()} [pydantic]
    → {k: v.model_dump() for k, v in self.remote_agents.items()} [pydantic]
    → self.message_router_summary() [from MessageRouterMixin] (message_router.py:89-100)
      → (self.config.data_dir / "inboxes").exists() [pathlib]
      IF exists:
        → inboxes_dir.iterdir() [pathlib]
        FOR each agent_dir:
          → agent_dir.glob("*.json") [pathlib]
    → self.get_hook_status() [from HookRouterMixin] (hook_router.py:148-157)
      [see GET /hooks/status]
    → self.sse_status() [from SSEMixin] (sse.py:38-43)
      → self.event_queue.qsize() [asyncio.Queue]
      → self.event_queue.maxsize [asyncio.Queue]
```

---

## Inbox

### GET /messages/inbox/{inbox_id}/count (http_server.py:420-424)
```
Handler: get_inbox_count (http_server.py:421)
  → cave.get_inbox(inbox_id) [from MessageRouterMixin] (message_router.py:53-64)
    → self._get_inbox_dir(agent_id) (message_router.py:20-23)
      → (self.config.data_dir / "inboxes" / agent_id) [pathlib]
      → inbox_dir.mkdir(parents=True, exist_ok=True) [pathlib]
    → sorted(inbox_dir.glob("*.json")) [pathlib]
    FOR each msg_file:
      → json.loads(msg_file.read_text()) [stdlib]
  → len(messages) [built-in]
```

---

## PAIA State

### GET /paias (http_server.py:428-430)
```
Handler: list_paias (http_server.py:429)
  → cave.paia_states [direct attribute access — Dict[str, PAIAState]]
  → {k: v.model_dump() for k, v in ...} [pydantic]
```

### POST /paias/{paia_id} (http_server.py:433-436)
```
Handler: update_paia (http_server.py:434)
  → cave.update_paia_state(paia_id, **data) [from PAIAStateMixin] (paia_state.py:21-35)
    IF paia_id not in self.paia_states:
      → PAIAState(paia_id=paia_id) [pydantic model construction] (models.py:32-48)
      → self.paia_states[paia_id] = state
    FOR key, value in updates.items():
      IF hasattr(state, key):
        → setattr(state, key, value) [built-in]
    → state.last_heartbeat = datetime.utcnow() [stdlib datetime]
    → self._emit_event("paia_state_changed", {...}) [from SSEMixin]
  → state.model_dump() [pydantic]
```

---

## Remote Agents

### POST /run_agent (http_server.py:440-442)
```
Handler: run_agent (http_server.py:441) — async
  → cave.spawn_remote(**request) [from RemoteAgentMixin] (remote_agent.py:23-77)
    → agent_id = f"{name}_{datetime.utcnow().strftime(...)}" [stdlib datetime]
    → handle = RemoteAgentHandle(agent_id=..., config={...}, status="pending", spawned_by=...)
      [pydantic model] (models.py:60-68)
    → self.remote_agents[agent_id] = handle
    → self._emit_event("remote_agent_spawned", {...}) [from SSEMixin]
    IF self.config.sdna_enabled:
      TRY:
        → from ..remote_agent import RemoteAgent, RemoteAgentConfig [lazy import]
        → RemoteAgentConfig(name=..., system_prompt=..., goal_template=..., **kwargs)
        → agent = RemoteAgent(config)
        → handle.status = "running"
        → result = await agent.run(inputs or {}) [sdna external — async]
        → handle.status = "completed" if result.success else "failed"
        → handle.result = result.__dict__
        → self._emit_event("remote_agent_completed", {...}) [from SSEMixin]
      EXCEPT ImportError:
        → handle.status = "failed"
        → handle.result = {"error": "SDNA not installed"}
      EXCEPT Exception:
        → handle.status = "failed"
        → handle.result = {"error": str(e)}
```

### GET /remote_agents (http_server.py:445-447)
```
Handler: list_remote_agents (http_server.py:446)
  → cave.remote_agents [direct attribute access — Dict[str, RemoteAgentHandle]]
  → {k: v.model_dump() for k, v in ...} [pydantic]
```

### GET /remote_agents/{agent_id} (http_server.py:450-453)
```
Handler: get_remote_agent (http_server.py:451)
  → cave.get_remote_status(agent_id) [from RemoteAgentMixin] (remote_agent.py:79-81)
    → self.remote_agents.get(agent_id) [dict.get]
  IF handle: → handle.model_dump() [pydantic]
  ELSE: → {"error": "not found"}
```

---

## SSE Events

### GET /events (http_server.py:457-459)
```
Handler: events (http_server.py:458) — async
  → StreamingResponse(cave.event_generator(), media_type="text/event-stream")
    [starlette StreamingResponse]
  → cave.event_generator() [from SSEMixin] (sse.py:32-36)
    INFINITE LOOP:
      → event = await self.event_queue.get() [asyncio.Queue.get — blocks]
      → yield f"data: {json.dumps(event)}\n\n" [stdlib json + async generator]
```

---

## Entry Point

### main() (http_server.py:463-469)
```
→ import uvicorn [external]
→ argparse.ArgumentParser() [stdlib argparse]
→ parser.add_argument("--port", type=int, default=8080)
→ parser.add_argument("--host", type=str, default="0.0.0.0")
→ args = parser.parse_args()
→ uvicorn.run(app, host=args.host, port=args.port) [uvicorn external]
```

---

## Mixin → Method Mapping

| Method Called by Server | Defined In | Mixin | File:Line |
|---|---|---|---|
| `list_config_archives()` | CAVEAgent direct | — | cave_agent.py:193 |
| `get_active_config()` | CAVEAgent direct | — | cave_agent.py:197 |
| `archive_config(name)` | CAVEAgent direct | — | cave_agent.py:179 |
| `inject_config(name)` | CAVEAgent direct | — | cave_agent.py:186 |
| `delete_config_archive(name)` | CAVEAgent direct | — | cave_agent.py:201 |
| `export_config_archive(name, dest)` | CAVEAgent direct | — | cave_agent.py:205 |
| `import_config_archive(src, name)` | CAVEAgent direct | — | cave_agent.py:209 |
| `get_loop_state()` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:37 |
| `start_loop(type, config)` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:49 |
| `stop_loop()` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:95 |
| `trigger_transition(event, data)` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:128 |
| `pause_loop()` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:164 |
| `resume_loop()` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:174 |
| `list_available_loops()` | LoopManagerMixin | LoopManagerMixin | loop_manager.py:184 |
| `get_dna_status()` | CAVEAgent direct | — | cave_agent.py:234 |
| `start_auto_mode(dna)` | CAVEAgent direct | — | cave_agent.py:215 |
| `stop_auto_mode()` | CAVEAgent direct | — | cave_agent.py:220 |
| `check_dna_transition()` | CAVEAgent direct | — | cave_agent.py:228 |
| `list_modules()` | **NOT DEFINED** | — | **MISSING** |
| `load_module(name, code)` | **NOT DEFINED** | — | **MISSING** |
| `unload_module(name)` | **NOT DEFINED** | — | **MISSING** |
| `get_module_history()` | **NOT DEFINED** | — | **MISSING** |
| `run_omnisanc()` | CAVEAgent direct | — | cave_agent.py:242 |
| `handle_hook(type, data)` | HookRouterMixin | HookRouterMixin | hook_router.py:37 |
| `scan_hooks()` | HookRouterMixin | HookRouterMixin | hook_router.py:128 |
| `list_hooks()` | HookRouterMixin | HookRouterMixin | hook_router.py:132 |
| `get_hook_status()` | HookRouterMixin | HookRouterMixin | hook_router.py:148 |
| `get_omnisanc_state()` | OmnisancMixin | OmnisancMixin | omnisanc.py:35 |
| `get_omnisanc_status()` | OmnisancMixin | OmnisancMixin | omnisanc.py:219 |
| `get_omnisanc_zone()` | OmnisancMixin | OmnisancMixin | omnisanc.py:57 |
| `is_omnisanc_enabled()` | OmnisancMixin | OmnisancMixin | omnisanc.py:92 |
| `enable_omnisanc()` | OmnisancMixin | OmnisancMixin | omnisanc.py:99 |
| `disable_omnisanc()` | OmnisancMixin | OmnisancMixin | omnisanc.py:118 |
| `get_metabrainhook_state()` | OmnisancMixin | OmnisancMixin | omnisanc.py:141 |
| `set_metabrainhook_state(on)` | OmnisancMixin | OmnisancMixin | omnisanc.py:150 |
| `get_metabrainhook_prompt()` | OmnisancMixin | OmnisancMixin | omnisanc.py:179 |
| `set_metabrainhook_prompt(content)` | OmnisancMixin | OmnisancMixin | omnisanc.py:191 |
| `get_paia_mode()` | CAVEAgent direct | — | cave_agent.py:308 |
| `set_paia_mode(mode)` | CAVEAgent direct | — | cave_agent.py:349 |
| `get_auto_mode()` | CAVEAgent direct | — | cave_agent.py:323 |
| `set_auto_mode(mode)` | CAVEAgent direct | — | cave_agent.py:338 |
| `_ensure_attached()` | CAVEAgent direct | — | cave_agent.py:126 |
| `_attach_to_session()` | CAVEAgent direct | — | cave_agent.py:109 |
| `inspect()` | CAVEAgent direct | — | cave_agent.py:131 |
| `get_inbox(id)` | MessageRouterMixin | MessageRouterMixin | message_router.py:53 |
| `update_paia_state(id, **kw)` | PAIAStateMixin | PAIAStateMixin | paia_state.py:21 |
| `spawn_remote(**request)` | RemoteAgentMixin | RemoteAgentMixin | remote_agent.py:23 |
| `get_remote_status(id)` | RemoteAgentMixin | RemoteAgentMixin | remote_agent.py:79 |
| `event_generator()` | SSEMixin | SSEMixin | sse.py:32 |
| `_emit_event(type, data)` | SSEMixin | SSEMixin | sse.py:20 |
| `message_router_summary()` | MessageRouterMixin | MessageRouterMixin | message_router.py:89 |
| `sse_status()` | SSEMixin | SSEMixin | sse.py:38 |

---

## Known Bugs Found During Trace

1. **`cave.config.main_agent_session` — AttributeError** (http_server.py:349,352,358,375,380,397,409,411)
   - `CAVEConfig` has no `main_agent_session` field. Correct path: `cave.config.main_agent_config.tmux_session`
   - Affects: GET /output, POST /input, GET /state, POST /command, POST /attach

2. **`cave.list_modules()`, `cave.load_module()`, `cave.unload_module()`, `cave.get_module_history()` — AttributeError** (http_server.py:174,181,191,199)
   - These methods are not defined on CAVEAgent or any mixin.
   - Affects: All /modules/* endpoints

3. **`self._active_loop.conditions` — AttributeError** (loop_manager.py:136,191)
   - `AgentInferenceLoop` (loops/base.py) has no `conditions` attribute.
   - Affects: POST /loops/trigger, GET /loops/available

4. **POST /attach session override doesn't work** (http_server.py:409)
   - Sets `cave.config.main_agent_session` (non-existent field) instead of `cave.config.main_agent_config.tmux_session`
   - `_attach_to_session()` reads from `self.config.main_agent_config.tmux_session`, so the override is ignored.
