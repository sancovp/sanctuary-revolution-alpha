# Session 21 Continuity - Hook Control + Self Commands

## What We Built This Session

### 1. Hook Control System (`game_wrapper/core/hook_control.py`)
- Toggle individual hooks on/off via `/tmp/hook_config.json`
- All 6 hook types: pretooluse, posttooluse, userpromptsubmit, notification, stop, subagentspawn
- API: `HookControl.enable(type)`, `.disable(type)`, `.toggle(type)`, `.is_enabled(type)`, `.get_all()`

### 2. Persona Control System (`game_wrapper/core/persona_control.py`)
- Toggle active persona via `/tmp/active_persona` file flag
- API: `PersonaControl.activate(name)`, `.deactivate()`, `.get_active()`, `.is_active()`

### 3. PAIA Claude Code Hooks (in `~/.claude/hooks/` and `/tmp/gnosys-plugin/hooks/`)
All hooks check `/tmp/hook_config.json` before executing:
- `paia_injection_hook.py` - UserPromptSubmit, injects persona + pending messages
- `paia_pretooluse.py` - Can block tools, modify inputs via `/tmp/paia_hooks/pretool_config.json`
- `paia_posttooluse.py` - Logs results, injects context
- `paia_notification.py` - Logs notifications to `/tmp/paia_hooks/notifications.jsonl`
- `paia_stop.py` - Logs stop events to `/tmp/paia_hooks/stop_events.jsonl`
- `paia_subagentspawn.py` - Can block types, inject prompts via `/tmp/paia_hooks/subagent_config.json`

### 4. Self Command Generator (`game_wrapper/core/self_command_generator.py`)
Instead of hardcoded bash scripts, generates variations on-the-fly:
- `RestartConfig` - tmux_session, autopoiesis, resume_enabled, custom messages
- `CompactConfig` - tmux_session, pre/post messages
- `InjectConfig` - tmux_session, message, press_enter
- `SelfCommandGenerator.execute_restart(config)`, `.execute_compact(config)`, `.execute_inject(config)`

### 5. HTTP API Endpoints (added to `game_wrapper/server/http_server.py`)

**Hook Control:**
- `GET /hooks` - all hook states
- `POST /hooks/{type}/enable` - enable one
- `POST /hooks/{type}/disable` - disable one
- `POST /hooks/{type}/toggle` - toggle one

**Persona Control:**
- `GET /persona` - current persona
- `POST /persona/{name}` - activate
- `DELETE /persona` - deactivate

**Self Commands:**
- `POST /self/restart` - configurable restart (tmux_session, autopoiesis, resume_enabled, post_restart_message)
- `POST /self/compact` - configurable compact (tmux_session, pre/post messages)
- `POST /self/inject` - inject message to tmux (tmux_session, message, press_enter)

## Control Flow

```
HTTP API → Control classes → File flags → Hooks read flags → Execute if enabled
                                    ↓
                     /tmp/hook_config.json (hook toggles)
                     /tmp/active_persona (persona name)
                     /tmp/paia_hooks/*.json (hook-specific configs)
                     /tmp/self_command_config.json (restart/compact configs)
```

## File Locations

**game_wrapper core:**
- `/tmp/sanctuary-system/game_wrapper/core/hook_control.py`
- `/tmp/sanctuary-system/game_wrapper/core/persona_control.py`
- `/tmp/sanctuary-system/game_wrapper/core/self_command_generator.py`

**Hooks (live):**
- `/home/GOD/.claude/hooks/paia_*.py`

**Hooks (plugin copy):**
- `/tmp/gnosys-plugin/hooks/paia_*.py`

### 6. Harness Client MCP (`game_wrapper/mcp/harness_client_mcp.py`)
Regular FastMCP (no TreeShell) that calls harness HTTP server:
- `hooks_list/enable/disable/toggle(hook_type)`
- `persona_get/activate(name)/deactivate()`
- `self_restart/compact/inject(...)`
- `harness_status/spawn/send/capture/stop()`

Add to gnosys_kit or use standalone. Uses `PAIA_HARNESS_URL` env var (default localhost:8765).

**ADDED TO STRATA:** `~/.config/strata/servers.json` now has `paia-harness` entry.
Access via gnosys_kit: `discover_server_actions` with server_names=["paia-harness"]

## Architecture

```
Harness Server (HTTP :8765)    ←──── Railgun / External
        ↑
        │ HTTP
        │
Harness Client MCP (stdio)     ←──── Claude Code (via gnosys_kit)
```

Server independent, MCP is thin HTTP client.

## Next Steps

1. **Test the hooks** - Enable via API, trigger, verify injection works
2. **Wire harness to hooks** - EventRouter writes to `/tmp/paia_hooks/pending_injection.json`, hooks read it
3. **Container packaging** - TWI image with harness + hooks
4. **Connect to Railgun** - Frontend talks to HTTP API

## Key Insight from Session 20 (Still Applies)

THE GOD STACK:
```
Claude Code
    + prompt injection (Heaven) → chain prompts
    + self-compact → manage context
    + context gauge visibility → know when to compact
    = temporally persistent LLM that manages itself
```

Single agent, no multi-agent complexity. Harness wraps one Claude Code instance.
