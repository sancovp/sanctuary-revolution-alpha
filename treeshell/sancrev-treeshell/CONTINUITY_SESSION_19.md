# Session 19 CONTINUITY - Game Wrapper Architecture

## What We Built This Session

### Location: `/tmp/sanctuary-system/game_wrapper/`

```
game_wrapper/
├── core/
│   ├── harness.py          # PAIA daemon + tmux control
│   ├── output_watcher.py   # Regex patterns for terminal events
│   ├── terminal_ui.py      # InTerminalNotification/Overlay/Panel
│   └── event_router.py     # Routes events to outputs
├── adapters/
│   ├── langchain_adapter.py    # ClaudeCodeChatModel (Heaven integration)
│   └── heaven_integration.py   # ClaudeCodeProvider factory
├── events/
│   ├── psyche/module.py
│   ├── world/module.py
│   ├── system/module.py
│   └── psychoblood/
│       ├── psychoblood.py      # 9-state machine
│       ├── observer_psychics.py # Meta-awareness levels
│       └── berserking.py       # Wangtang formula
├── server/
│   └── http_server.py      # FastAPI + SSE for Railgun
└── utils/
    └── rng/base.py         # RNGEvent, RNGModule
```

---

## Key Architecture Decisions

### Two Output Channels
Events from psyche/world/system can route to:
1. **InTerminalObject** - Visual display (tmux popups/notifications/panels)
2. **HookInjection** - Context injection into Claude Code

### tmux Capabilities Discovered
- `capture-pane -p` = READ terminal as string
- `send-keys` = WRITE to terminal
- `display-popup` = INTERACTIVE floating windows (user can type!)
- `split-window` = Persistent side panels
- `-S/-E` flags = Control scrollback range

### Event Flow
```
Event Sources          →  EventRouter  →  Output Channels
───────────────           ───────────     ────────────────
Psyche (internal)    ─┐                ┌→ InTerminalObject (visual)
World (external)     ─┼→  route()     ─┼→ HookInjection (context)
System (infra)       ─┘                └→ SSE (Railgun)
Detected (terminal)  ─┘
```

### Heaven Integration
```python
# ClaudeCodeChatModel implements LangChain BaseChatModel
# So Heaven can use Claude Code like any other provider:

chat = ClaudeCodeProvider.create(agent_command="claude")
response = chat.invoke([HumanMessage("do something")])
# Under the hood: tmux send-keys → Claude Code → tmux capture-pane
```

---

## CRITICAL DISCOVERY: tmux display-popup is INTERACTIVE

User can TYPE into popup windows. This enables:
- Command palettes
- Game menus
- Input dialogs
- Mini-terminals

The sanctuary revolution game interface can be built entirely in tmux.

---

## Files Created

| File | Purpose |
|------|---------|
| `core/harness.py` | tmux control, daemon loop, event watching |
| `core/output_watcher.py` | Regex patterns for block reports, giint, logs |
| `core/terminal_ui.py` | InTerminalNotification, InTerminalOverlay, InTerminalPanel |
| `core/event_router.py` | Routes events to terminal/hooks/SSE |
| `server/http_server.py` | FastAPI with SSE streaming for Railgun |
| `adapters/langchain_adapter.py` | ClaudeCodeChatModel for Heaven |
| `adapters/heaven_integration.py` | ClaudeCodeProvider factory |

---

## Next Session TODO

1. ~~**Wire event_router into harness**~~ ✅ DONE - harness now has router + terminal_ui
2. ~~**Create hook that reads pending_injection.json**~~ ✅ DONE - `/home/GOD/.claude/hooks/paia_injection_hook.py`
3. **Register the hook** - Add to settings.json under UserPromptSubmit hooks
4. **Test the full loop** - event → terminal notification → hook injection
5. **Test Heaven integration** - ClaudeCodeProvider.create() → invoke()
6. **Build command palette** - Interactive tmux popup menu for game actions

### Hook Registration Needed
Add to `/home/GOD/.claude/settings.json` or `settings.local.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": ["python3 /home/GOD/.claude/hooks/paia_injection_hook.py"]
      }
    ]
  }
}
```

---

## Key Insight

**The harness is the control plane.** Everything else (Claude Code, MCPs, hooks) are just processes being puppeted via tmux. Single Python runtime controls all.

**tmux gives us:**
- Full terminal read/write
- Interactive overlays
- Persistent panels
- Session management

**This IS the sanctuary revolution game interface.**

---

*Session 19 (2026-01-12)*
