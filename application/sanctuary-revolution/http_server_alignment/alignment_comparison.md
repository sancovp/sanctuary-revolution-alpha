# Sancrev -> CAVE Alignment: What Needs Porting

## Architecture Context

CAVE (`/tmp/cave/cave/server/http_server.py`) is the canonical base infrastructure layer. Its god object `CAVEAgent` is composed of 10 mixins: PAIAStateMixin, AgentRegistryMixin, MessageRouterMixin, HookRouterMixin, LoopManagerMixin, RemoteAgentMixin, SSEMixin, OmnisancMixin, AnatomyMixin, TUIMixin.

Sancrev (`/tmp/sanctuary-revolution/sanctuary_revolution/harness/server/http_server.py`) is the application layer (the "Sanctuary Revolution" game). It was built FIRST, before CAVE existed. CAVE was extracted from it as a canonical base, but sancrev was NEVER refactored to inherit from CAVE. It uses its own standalone code (PAIAHarness, HookControl, PersonaControl, SelfCommandGenerator, llegos, domain builders) instead of extending CAVEAgent.

The goal: refactor sancrev to EXTEND CAVE. Every sancrev capability must either already exist in CAVE (inherit it), need to be ported INTO CAVE (as a new mixin/method), or stay in sancrev only (game-specific application logic).

---

## Category 1: Already In CAVE (sancrev can just inherit)

These sancrev endpoints have functional equivalents in CAVE. After refactoring, sancrev would inherit these from CAVEAgent and would not need its own implementation.

| # | Sancrev Endpoint | CAVE Equivalent | Difference in Implementation |
|---|---|---|---|
| 1 | `GET /events` (SSE stream, line 261) | `GET /events` (SSE stream) | Sancrev uses `asyncio.wait_for` with 30s keepalive timeout. CAVE blocks on `Queue.get()` with no keepalive. Sancrev's keepalive is better for production (prevents connection drops); CAVE should adopt it, but the base capability exists. |
| 2 | `GET /capture` (terminal capture, line 283) | `GET /output` (terminal capture) | Both call tmux `capture-pane` via subprocess. Sancrev uses `PAIAHarness.capture_pane(500)`. CAVE uses `CodeAgent.capture_pane(lines)` and additionally parses context percentage via `ClaudeStateReader.parse_context_pct()`. CAVE's version is richer. |
| 3 | `GET /hooks` (list hooks, line 301) | `GET /hooks` (list hooks) | Sancrev returns `HookControl.get_all()` — flat dict of `hook_type -> bool` from `/tmp/hook_config.json`. CAVE returns `HookRouterMixin.list_hooks()` — registry of class/script hook objects with metadata. Different data models, but both list hooks. Sancrev's simple model is a subset of CAVE's richer model. |
| 4 | `GET /status` (health/status, line 187) | `GET /health` | Sancrev returns `{running, session_exists, tmux_session, agent_command}`. CAVE returns `{"status": "ok", "version": "0.1.0"}`. Both are health checks. Sancrev's is richer but the base capability exists; sancrev can override to add fields. |
| 5 | `GET /messages/inbox/{agent_id}/count` (line 1471) | `GET /messages/inbox/{inbox_id}/count` | Both return inbox message counts. Sancrev uses `CodeAgent._inbox` (in-memory deque) with optional unread filter. CAVE uses `MessageRouterMixin.get_inbox()` (file-based JSON). Different storage backends, same conceptual capability. |

---

## Category 2: NOT In CAVE -- Needs Porting (new mixin/method needed)

These sancrev endpoints have NO equivalent in CAVE. For sancrev to extend CAVE, these capabilities must be added to CAVE first (as new mixins or methods on existing mixins). Grouped by suggested CAVE location.

### 2A. Session Lifecycle (new `SessionManagerMixin` or extend CAVEAgent directly)

CAVE can only attach to existing tmux sessions. Sancrev can create, spawn, stop, and fully manage session lifecycles. CAVE needs session creation/management to be a proper base.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 1 | `POST /spawn` (line 165) | Creates new tmux session via `PAIAHarness.start()` -> `create_session()` -> `subprocess.run(["tmux", "new-session", ...])`, then spawns agent command via `send_keys`, waits 2s. | New `SessionManagerMixin` or extend `_attach_to_session()` on CAVEAgent to support create-if-not-exists. |
| 2 | `POST /stop` (line 291) | Sets `harness.running = False`, stops harness. | `SessionManagerMixin` — add `stop()` method. Currently CAVE's shutdown handler is a no-op. |
| 3 | `POST /send` (line 200) | Sends prompt to agent AND waits for response with polling (`send_and_wait`: captures pane, sends text, polls until stable_count >= 3 and response marker detected). | Extend CAVEAgent's `POST /input` equivalent. CAVE's current `send_keys()` is fire-and-forget. The send-and-wait-for-response pattern is needed for synchronous interactions. Could go on CAVEAgent directly or a new mixin. |

### 2B. Persona Control (new `PersonaMixin`)

CAVE has zero persona concept. Sancrev manages active persona via a file flag (`/tmp/active_persona`). This is a general-purpose infrastructure concern (which persona is the agent running as), not game-specific.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 4 | `GET /persona` (line 336) | Reads `/tmp/active_persona` via `PersonaControl.is_active()` + `PersonaControl.get_active()`. Returns active persona name and whether one is active. | New `PersonaMixin` on CAVEAgent. |
| 5 | `POST /persona/{name}` (line 345) | Writes persona name to `/tmp/active_persona` via `PersonaControl.activate(name)`. | `PersonaMixin.activate_persona(name)` |
| 6 | `DELETE /persona` (line 352) | Deletes `/tmp/active_persona` via `PersonaControl.deactivate()`. | `PersonaMixin.deactivate_persona()` |

### 2C. Self Commands (new `SelfCommandMixin`)

CAVE has `POST /command` which sends slash commands, and `POST /input` which sends text. But it lacks the ability to restart Claude Code, generate restart/compact scripts, or perform structured self-commands.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 7 | `POST /self/restart` (line 380) | Generates bash restart script with tmux commands (optional resume, autopoiesis message), writes to `/tmp/paia_restart_handler.sh`, chmod 755, executes via `nohup Popen` (detached process). Uses `SelfCommandGenerator.execute_restart()`. | New `SelfCommandMixin` on CAVEAgent. Self-restart is infrastructure-level. |
| 8 | `POST /self/compact` (line 393) | Generates bash compact script with tmux compact commands, executes via `subprocess.run(["bash", "-c", script])`. Uses `SelfCommandGenerator.execute_compact()`. | `SelfCommandMixin.compact()`. CAVE's `POST /command` can send `/compact` but does not generate proper scripts with pre/post steps. |
| 9 | `POST /self/inject` (line 405) | Generates bash script with tmux `send-keys` for message injection (optional Enter), executes via `subprocess.run`. Uses `SelfCommandGenerator.execute_inject()`. | `SelfCommandMixin.inject()`. CAVE's `POST /input` does the same thing directly via `CodeAgent.send_keys()` — this is close to a duplicate, but the script-generation approach allows for more complex injection sequences. |

### 2D. Code Execution (new `CodeExecutionMixin`)

CAVE has no ability to run arbitrary code. This is an infrastructure concern (running test scripts, automation code, etc.).

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 10 | `POST /execute` (line 425) | Runs python or bash code via `subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=req.timeout)`. Returns stdout, stderr, return_code, execution_time. | New `CodeExecutionMixin` on CAVEAgent. |

### 2E. Claude Process Control (extend CAVEAgent or new `ProcessControlMixin`)

CAVE can send text/commands to tmux but cannot interrupt, force-exit, or kill the Claude process. These are infrastructure-level operations needed for any application that controls a Claude Code session.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 11 | `POST /interrupt` (line 461) | Sends Escape key (or double Escape with 50ms gap) to tmux session via `subprocess.run(["tmux", "send-keys", "-t", session, "Escape"])`. | New `ProcessControlMixin` or extend CAVEAgent. |
| 12 | `POST /force_exit` (line 485) | Sends `C-c` to tmux session via `subprocess.run(["tmux", "send-keys", "-t", session, "C-c"])`. | `ProcessControlMixin.force_exit()` |
| 13 | `POST /kill_agent_process` (line 495) | Finds claude PIDs via `ps aux | grep '[c]laude' | awk '{print $2}'`, then `kill -9` each PID. | `ProcessControlMixin.kill_process()` |

### 2F. Event Injection (extend `SSEMixin`)

CAVE's `_emit_event()` is internal-only. Sancrev has two public mechanisms for injecting events that CAVE lacks.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 14 | `POST /event` (line 231) | Pushes arbitrary event dict to `_event_queue` for SSE broadcast. Any external caller can inject events. | Extend `SSEMixin` — add a public `push_event()` method exposed via HTTP. |
| 15 | `POST /inject` (line 221) | Writes message to `/tmp/paia_injection.txt` for OutputWatcher pickup, fires events via `harness._emit_event()` to registered callbacks. | Extend `SSEMixin` or new injection mechanism. The file-based injection pattern (`/tmp/paia_injection.txt`) is used by hooks to inject context into Claude's next response. |

### 2G. Hook Control Granularity (extend `HookRouterMixin`)

CAVE has hook management but only allows setting the entire active_hooks dict at once. Sancrev has per-hook-type enable/disable/toggle which is more ergonomic.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 16 | `POST /hooks/{hook_type}/enable` (line 307) | Enables single hook type by setting `config[hook_type] = True` in `/tmp/hook_config.json` via `HookControl.enable()`. | Extend `HookRouterMixin` — add `enable_hook(hook_type)`, `disable_hook(hook_type)`, `toggle_hook(hook_type)` methods. |
| 17 | `POST /hooks/{hook_type}/disable` (line 316) | Disables single hook type by setting `config[hook_type] = False`. | Same as above. |
| 18 | `POST /hooks/{hook_type}/toggle` (line 325) | Toggles single hook type via `config[hook_type] = not config.get(hook_type, False)`. | Same as above. |

### 2H. Agent Registry HTTP Endpoints (extend `AgentRegistryMixin`)

CAVE has `AgentRegistryMixin` with `register_agent()` and `unregister_agent()` methods, but these are NOT exposed via HTTP endpoints. Sancrev exposes them. CAVE also lacks agent relay (forwarding commands to remote agents).

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 19 | `POST /agents/register` (line 1182) | Stores `AgentRegistration(agent_id, name, address, capabilities)` in `_agent_registry` dict. | Expose existing `AgentRegistryMixin.register_agent()` via HTTP endpoint. |
| 20 | `DELETE /agents/{agent_id}` (line 1190) | Removes agent from `_agent_registry` dict. | Expose existing `AgentRegistryMixin.unregister_agent()` via HTTP endpoint. |
| 21 | `GET /agents` (line 1199) | Lists all registered agents as `{agent_id: registration.model_dump()}`. | Expose existing `AgentRegistryMixin` data via HTTP endpoint. |
| 22 | `GET /agents/{agent_id}` (line 1208) | Returns single agent registration by ID. | Add to `AgentRegistryMixin` — `get_agent(agent_id)`. |
| 23 | `POST /agents/{agent_id}/execute` (line 1216) | Relays code execution to remote agent via `httpx.AsyncClient().post(f"{reg.address}/execute", ...)`. | New `AgentRelayMixin` or extend `AgentRegistryMixin` with relay methods. |
| 24 | `POST /agents/{agent_id}/interrupt` (line 1237) | Relays interrupt to remote agent via `httpx.AsyncClient().post(f"{reg.address}/interrupt", ...)`. | Same as above. |
| 25 | `POST /agents/{agent_id}/inject` (line 1253) | Relays injection to remote agent via `httpx.AsyncClient().post(f"{reg.address}/self/inject", ...)`. | Same as above. |
| 26 | `POST /agents/instance/register` (line 1605) | Registers CodeAgent instance (in-memory object) for inbox routing. Separate from registry (registry = metadata, instance = live object). | `AgentRegistryMixin` — add instance tracking alongside registration metadata. |

### 2I. Messaging System (new `MessagingMixin` or major extension of `MessageRouterMixin`)

CAVE has `MessageRouterMixin` with file-based JSON inboxes and basic routing, but it is minimal: only `route_message()`, `get_inbox()`, `ack_message()`, and `message_router_summary()` — and only `get_inbox_count` is exposed via HTTP. Sancrev has a full llegos-based messaging system with send, reply, forward, threading, priority, read/unread tracking, and message history. This is the largest gap.

| # | Sancrev Endpoint | What It Does (from callgraph) | Suggested CAVE Location |
|---|---|---|---|
| 27 | `POST /messages/send` (line 1331) | Creates `UserPromptMessage`, stores in `_message_store`, enqueues to target `CodeAgent._inbox` (priority-sorted deque), fires SSE event for human-targeted messages. | Extend `MessageRouterMixin` or new `MessagingMixin`. Core message creation + routing + store. |
| 28 | `POST /messages/reply` (line 1380) | Uses `llegos Message.reply()` to create reply linked to parent message, stores in `_message_store`, enqueues to parent's sender. | `MessagingMixin` — reply chain support. |
| 29 | `GET /messages/thread/{message_id}` (line 1409) | Uses `llegos message_chain(msg, height)` to traverse parent chain up to `height` hops. Returns serialized thread. | `MessagingMixin` — thread traversal. |
| 30 | `GET /messages/{message_id}` (line 1425) | Returns single message from `_message_store` by ID. | `MessagingMixin` — message store with ID lookup. |
| 31 | `GET /messages/inbox/{agent_id}` (line 1434) | Returns full inbox contents with read/unread status. Uses `CodeAgent._inbox` (deque) or falls back to scanning `_message_history`. | Extend `MessageRouterMixin` — full inbox contents, not just count. |
| 32 | `GET /messages/inbox/{agent_id}/peek` (line 1509) | Returns highest-priority message without removing it. Uses `CodeAgent.peek()` which sorts by `(-priority, created_at)`. | `MessagingMixin` — priority-aware peek. |
| 33 | `GET /messages/inbox/{agent_id}/pop` (line 1520) | Removes and returns highest-priority message. Uses `CodeAgent.dequeue()` which sorts, removes first, emits event. | `MessagingMixin` — priority-aware dequeue. |
| 34 | `DELETE /messages/inbox/{agent_id}/{message_id}` (line 1531) | Acknowledges/removes specific message from `CodeAgent._inbox` by ID. | Extend `MessageRouterMixin.ack_message()` — expose via HTTP. |
| 35 | `GET /messages/history` (line 1545) | Returns ordered `_message_history` (list of message IDs) with optional agent filter, sliced by limit. | `MessagingMixin` — message history store. |
| 36 | `POST /messages/forward` (line 1570) | Uses `llegos Message.forward_to()` to create forwarded copy, stores and enqueues to target. | `MessagingMixin` — message forwarding. |
| 37 | `PUT /messages/thread/{message_id}/alias` (line 1624) | Traverses to thread root via parent chain, sets `root.metadata["thread_alias"]` to given name. | `MessagingMixin` — thread metadata management. |
| 38 | `GET /messages/thread/{message_id}/alias` (line 1650) | Traverses to thread root, returns `root.metadata.get("thread_alias")`. | Same as above. |
| 39 | `PUT /messages/thread/{message_id}/priority` (line 1669) | Traverses to thread root, sets `root.metadata["thread_priority"]` to urgent/normal/low. | Same as above. |
| 40 | `DELETE /messages/thread/{message_id}/alias` (line 1688) | Traverses to thread root, removes `thread_alias` from metadata. | Same as above. |
| 41 | `GET /threads` (line 1708) | Scans all `_message_history`, finds unique thread roots, counts messages per thread, returns `{root_id, alias, message_count, created_at, preview}`. Optional alias substring filter. | `MessagingMixin` — thread listing/discovery. |
| 42 | `POST /messages/{message_id}/read` (line 1767) | Adds `agent_id` to `_read_status[message_id]` set. | `MessagingMixin` — read receipt tracking. |
| 43 | `DELETE /messages/{message_id}/read` (line 1786) | Removes `agent_id` from `_read_status[message_id]` set. | Same as above. |
| 44 | `GET /messages/{message_id}/read_by` (line 1802) | Returns list of agent_ids that have read the message. | Same as above. |
| 45 | `GET /messages/{message_id}/is_read` (line 1816) | Returns bool whether specific agent has read specific message. | Same as above. |

### Summary: What CAVE Needs

| New CAVE Component | Sancrev Endpoints Covered | Priority |
|---|---|---|
| `SessionManagerMixin` (create/stop sessions) | 3 endpoints (#1-3) | HIGH — CAVE cannot create sessions at all |
| `PersonaMixin` (persona activation) | 3 endpoints (#4-6) | MEDIUM — simple file flag, but needed for any game |
| `SelfCommandMixin` (restart/compact/inject scripts) | 3 endpoints (#7-9) | HIGH — self-restart is critical for autonomous operation |
| `CodeExecutionMixin` (run python/bash) | 1 endpoint (#10) | MEDIUM — useful for automation |
| `ProcessControlMixin` (interrupt/force-exit/kill) | 3 endpoints (#11-13) | HIGH — needed to control Claude process |
| `SSEMixin` extension (public event push + injection file) | 2 endpoints (#14-15) | MEDIUM — external event injection |
| `HookRouterMixin` extension (per-hook enable/disable/toggle) | 3 endpoints (#16-18) | LOW — convenience over existing bulk-set |
| `AgentRegistryMixin` extension + `AgentRelayMixin` | 8 endpoints (#19-26) | HIGH — registry exists but is not HTTP-exposed; relay is new |
| `MessagingMixin` (full llegos messaging) | 19 endpoints (#27-45) | HIGH — largest gap; CAVE's MessageRouterMixin is minimal |

**Total: 45 sancrev endpoints need their capabilities ported into CAVE.**

---

## Category 3: Game-Specific (stays in sancrev only, NOT ported to CAVE)

These sancrev endpoints are application-layer game logic specific to the Sanctuary Revolution game. They use domain-specific builders (CAVEBuilder for business, SANCTUMBuilder for life architecture, PAIABuilder for agent construction) and game scoring systems (GEAR). These should NOT be in the CAVE base -- they stay in sancrev as the application layer that extends CAVE.

### 3A. GEAR Events (game scoring system)

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 1 | `POST /gear/accept` (line 585) | Handles GEAR acceptance proofs via `GEARProofHandler` dispatching to dimension-specific handlers (COMPONENT_ACCEPTED, ACHIEVEMENT_VALIDATED, REALITY_GROUNDED, PROOF_REJECTED). Updates PAIA gear_state dimensions. |
| 2 | `POST /gear/emit` (line 611) | Emits GEAR state to `EventRouter` which routes to terminal notification + hook injection + SSE. Reads PAIA from store, reads gear_state. |
| 3 | `GET /gear/{paia_name}` (line 626) | Returns GEAR state for a PAIA: level, phase, total_points, overall score, per-dimension scores (gear, experience, achievements, reality) with last 5 notes each. |
| 4 | `POST /gear/register` (line 649) | Registers a PAIA to the JSON store file (`/tmp/heaven_data/paia_store.json`) via `paia_builder.models.PAIA.model_validate()` + `set_paia()`. |
| 5 | `GET /gear/list` (line 666) | Lists all registered PAIA names from the store file. |

### 3B. CAVE Builder (business domain)

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 6 | `GET /cave/list` (line 678) | Lists all caves (business entities) via `CAVEBuilder.list_caves()` from `/tmp/cave-builder/` storage. Returns name, MRR, journey count, framework count, is_complete. |
| 7 | `GET /cave/status` (line 685) | Returns current selected cave's full status string via `CAVEBuilder.status()`. |
| 8 | `GET /cave/offers` (line 694) | Lists value ladder offers (stage, name, price) from current cave via `CAVEBuilder.list_offers()`. |
| 9 | `GET /cave/journeys` (line 704) | Lists customer journeys (title, domain, published) from current cave via `CAVEBuilder.list_journeys()`. |

### 3C. SANCTUM Builder (life architecture domain)

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 10 | `GET /sanctum/list` (line 717) | Lists all sanctums via `SANCTUMBuilder.list_sanctums()` from `/tmp/sanctum-builder/` storage. Returns name, overall score. |
| 11 | `GET /sanctum/status` (line 724) | Returns current sanctum's SOSEEH-themed status string via `SANCTUMBuilder.status()`. |
| 12 | `GET /sanctum/rituals` (line 733) | Lists rituals (name, domain, frequency) from current sanctum. |
| 13 | `GET /sanctum/goals` (line 745) | Lists goals (name, domain, progress) from current sanctum. |

### 3D. PAIAB Builder -- Management (agent construction game)

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 14 | `GET /paiab/list` (line 906) | Lists all PAIAs via `PAIABuilder.list_paias()` (persistent file-based definitions). |
| 15 | `GET /paiab/status` (line 912) | Returns PAIA construction status: pilot/vehicle/mission_control/loops + GEAR state display via `PAIABuilder.status()`. |
| 16 | `GET /paiab/which` (line 922) | Returns currently selected PAIA name via `PAIABuilder.which()`. |
| 17 | `POST /paiab/select/{name}` (line 927) | Selects active PAIA via `PAIABuilder.select(name)`. |
| 18 | `POST /paiab/new` (line 933) | Creates new PAIA with optional git dir + GIINT project via `PAIABuilder.new()`. |
| 19 | `DELETE /paiab/{name}` (line 939) | Deletes PAIA via `PAIABuilder.delete()`. |
| 20 | `POST /paiab/fork` (line 945) | Forks existing PAIA into new one via `PAIABuilder.fork_paia()`. |
| 21 | `POST /paiab/tick_version` (line 951) | Version-bumps PAIA via `PAIABuilder.tick_version()`. |

### 3E. PAIAB Builder -- Components (9 component types)

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 22 | `GET /paiab/components/{comp_type}` (line 960) | Lists components of given type (skills, mcps, hooks, commands, agents, personas, plugins, flights, metastacks) with tier/golden/points. |
| 23 | `GET /paiab/component/{comp_type}/{name}` (line 969) | Returns single component detail (name, description, tier, golden, points, notes). |
| 24 | `DELETE /paiab/component/{comp_type}/{name}` (line 974) | Removes component from PAIA. |
| 25 | `POST /paiab/add/skill` (line 983) | Adds skill spec to PAIA. Creates spec, appends, logs experience, updates construction docs, syncs GIINT. |
| 26 | `POST /paiab/add/mcp` (line 989) | Adds MCP spec to PAIA. Same pattern. |
| 27 | `POST /paiab/add/hook` (line 995) | Adds hook spec to PAIA. Same pattern. |
| 28 | `POST /paiab/add/command` (line 1001) | Adds command spec to PAIA. Same pattern. |
| 29 | `POST /paiab/add/agent` (line 1007) | Adds agent spec to PAIA. Same pattern. |
| 30 | `POST /paiab/add/persona` (line 1013) | Adds persona spec to PAIA. Same pattern. |
| 31 | `POST /paiab/add/plugin` (line 1019) | Adds plugin spec to PAIA. Same pattern. |
| 32 | `POST /paiab/add/flight` (line 1025) | Adds flight spec to PAIA. Same pattern. |
| 33 | `POST /paiab/add/metastack` (line 1031) | Adds metastack spec to PAIA. Same pattern. |

### 3F. PAIAB Builder -- Tier/Golden Advancement

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 34 | `POST /paiab/advance_tier` (line 1040) | Advances component tier, logs experience, emits GEAR event, updates GIINT. |
| 35 | `POST /paiab/set_tier` (line 1046) | Sets component tier directly (override). |
| 36 | `POST /paiab/goldify` (line 1052) | Advances component golden status, logs experience. |
| 37 | `POST /paiab/regress_golden` (line 1058) | Regresses component golden status with reason. |

### 3G. PAIAB Builder -- GEAR Integration

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 38 | `POST /paiab/update_gear` (line 1067) | Updates GEAR dimension score (gear/experience/achievements/reality) with note, emits event. |
| 39 | `POST /paiab/sync_gear` (line 1073) | Syncs GEAR state from component data, emits full state. |
| 40 | `GET /paiab/check_win` (line 1079) | Checks if PAIA is fully constructed (win condition). If yes and git_dir exists, writes CLAUDE.md + gear status doc. |
| 41 | `POST /paiab/publish` (line 1085) | Publishes PAIA via `utils.publish_paia()`. |

### 3H. PAIAB Builder -- Field Setters (11 endpoints)

| # | Sancrev Endpoint | What It Does |
|---|---|---|
| 42 | `POST /paiab/set/skill_md` (line 1094) | Sets SKILL.md content on skill spec, saves, completes GIINT task. |
| 43 | `POST /paiab/set/skill_reference` (line 1100) | Sets reference.md content on skill spec. |
| 44 | `POST /paiab/set/skill_resource` (line 1106) | Adds resource file (filename, content, content_type) to skill spec. |
| 45 | `POST /paiab/set/mcp_server` (line 1112) | Sets MCP server definition (`OnionLayerSpec`) on MCP spec. |
| 46 | `POST /paiab/set/mcp_tool` (line 1118) | Adds MCP tool (core_function, ai_description) to MCP spec. |
| 47 | `POST /paiab/set/hook_script` (line 1124) | Sets hook script content on hook spec. |
| 48 | `POST /paiab/set/command_prompt` (line 1130) | Sets command prompt content on command spec. |
| 49 | `POST /paiab/set/agent_prompt` (line 1136) | Sets agent system prompt on agent spec. |
| 50 | `POST /paiab/set/persona_frame` (line 1142) | Sets persona frame content on persona spec. |
| 51 | `POST /paiab/set/flight_step` (line 1148) | Adds flight step (number, title, instruction, skills) to flight spec. |
| 52 | `POST /paiab/set/metastack_field` (line 1154) | Adds metastack field (name, type, description, default) to metastack spec. |

### 3I. EventRouter (game-specific event routing)

Sancrev's `EventRouter` routes events to terminal UI notifications, hook injection files, and SSE callbacks. This is tightly coupled to the game's `TerminalUI`, `OutputWatcher`, and domain-specific event types (`GEAREventType`, `GEARDimensionType`). CAVE has `SSEMixin` for event emission but not the full routing to terminal/hooks.

Note: The EventRouter PATTERN could be ported to CAVE as a general routing mechanism, but the current implementation is deeply entangled with game-specific event types and builders. Recommend keeping game-specific routing in sancrev and having CAVE provide the base SSE + hook injection primitives that sancrev's EventRouter can use.

**Total: 53 sancrev endpoints are game-specific and stay in sancrev.**

---

## Final Counts

| Category | Endpoint Count | Description |
|---|---|---|
| **Category 1**: Already in CAVE | **5** | Sancrev inherits these; no new CAVE code needed |
| **Category 2**: Needs porting to CAVE | **45** | New mixins/methods required in CAVE |
| **Category 3**: Game-specific (stays in sancrev) | **53** | Application-layer; sancrev-only |
| **TOTAL** | **103** | All sancrev endpoints accounted for |

### Porting Effort by New CAVE Component

| New CAVE Component | Endpoints | Complexity | Notes |
|---|---|---|---|
| `MessagingMixin` | 19 | **LARGE** | Full llegos replacement. Send/reply/forward/thread/read-status. Biggest single piece of work. |
| `AgentRegistryMixin` extension + `AgentRelayMixin` | 8 | **MEDIUM** | Registry HTTP exposure is easy. Relay (httpx forwarding) is new. |
| `SessionManagerMixin` | 3 | **MEDIUM** | Create session + spawn agent + send-and-wait. |
| `PersonaMixin` | 3 | **SMALL** | Simple file flag read/write. |
| `SelfCommandMixin` | 3 | **MEDIUM** | Script generation + nohup execution. |
| `ProcessControlMixin` | 3 | **SMALL** | tmux send-keys for Escape/C-c + ps/kill. |
| `CodeExecutionMixin` | 1 | **SMALL** | subprocess.run wrapper. |
| `SSEMixin` extension | 2 | **SMALL** | Add public push_event + injection file write. |
| `HookRouterMixin` extension | 3 | **SMALL** | Per-hook enable/disable/toggle. |

---

## Appendix: CAVE-Only Capabilities (no sancrev equivalent)

For completeness, these CAVE capabilities have NO sancrev equivalent. They do NOT need porting (they are already in CAVE). But sancrev will gain them for free once it extends CAVE.

| CAVE Capability | Endpoints | What Sancrev Gains |
|---|---|---|
| Config Archive System | 7 endpoints (GET/POST/DELETE /configs/*) | Archive, inject, export, import Claude Code configuration snapshots with SHA-256 hash detection. |
| Loop Manager | 7 endpoints (GET/POST /loops/*) | Start/stop/pause/resume AgentInferenceLoops (autopoiesis, guru, omnisanc) with hook lifecycle. |
| DNA / Auto Mode | 3 endpoints (GET/POST /dna/*) | Orchestrate loop sequences with cycle/one_shot exit behavior and TransitionAction chains. |
| Omnisanc State Control | 6 endpoints (GET/POST /omnisanc/*) | Zone detection (HOME/STARPORT/LAUNCH/SESSION/LANDING/MISSION), enable/disable. |
| Metabrainhook Control | 4 endpoints (GET/POST /metabrainhook/*) | On/off state + prompt content management. |
| PAIA Mode Control | 3 endpoints (GET/POST /paia/*) | DAY/NIGHT + AUTO/MANUAL mode. |
| Hook Signal Execution | 1 endpoint (POST /hook/{hook_type}) | The core brain loop: run_omnisanc -> handle_hook (class/script execution + capability RAG) -> check_dna_transition. |
| Hook Scanning | 1 endpoint (POST /hooks/scan) | Dynamic hook class loading via importlib. |
| Active Hooks Management | 2 endpoints (GET/POST /hooks/active) | Named hooks per type dict with config persistence. |
| Comprehensive State Reader | 1 endpoint (GET /state) | ClaudeStateReader: settings, MCP config, project state, hooks, skills, rules, plugins, subagents. |
| Remote Agent Spawning | 3 endpoints (POST/GET /run_agent, /remote_agents) | SDNA RemoteAgent (async) with lifecycle tracking. |
| PAIA Runtime State | 2 endpoints (GET/POST /paias) | Update runtime PAIAState with heartbeat + SSE emission. |
| Inspect | 1 endpoint (GET /inspect) | Full god object state dump. |
| Module System | 4 endpoints (/modules/*) | **BROKEN** — methods not defined on CAVEAgent. All will raise AttributeError. |

**Total: 45 CAVE-only endpoints that sancrev gains by inheritance.**

---

## Appendix: CAVE Bugs to Fix Before Sancrev Extension

These bugs in CAVE should be fixed before sancrev attempts to extend it.

1. **`cave.config.main_agent_session` -- AttributeError** (http_server.py lines 349, 352, 358, 375, 380, 397, 409, 411)
   - `CAVEConfig` has no `main_agent_session` field. Correct path: `cave.config.main_agent_config.tmux_session`
   - Affects 5 endpoints: GET /output, POST /input, GET /state, POST /command, POST /attach

2. **`cave.list_modules()` etc. -- AttributeError** (http_server.py lines 174, 181, 191, 199)
   - `list_modules`, `load_module`, `unload_module`, `get_module_history` are NOT DEFINED on CAVEAgent or any mixin.
   - Affects all 4 /modules/* endpoints. Either implement a `ModuleMixin` or remove the dead endpoints.

3. **`self._active_loop.conditions` -- AttributeError** (loop_manager.py lines 136, 191)
   - `AgentInferenceLoop` (loops/base.py) has no `conditions` attribute.
   - Affects: POST /loops/trigger, GET /loops/available

4. **POST /attach session override silently ignored** (http_server.py line 409)
   - Sets `cave.config.main_agent_session` (creates dynamic attribute) instead of `cave.config.main_agent_config.tmux_session`
   - `_attach_to_session()` reads from the correct path, so the override has no effect.
