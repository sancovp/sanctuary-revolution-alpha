# Hooks and Loops Architecture

## The Hierarchy

```
META BRAINHOOK (Level 2 - Failsafe)
└── Observe & report when everything dies

OMNISANC (Level 1 - Orchestrator)
└── State machine + MCP manager + queue

INTERACTION LOOPS (Level 0 - Normal operation)
├── autopoiesis (self-continuation)
├── guru (emanation required)
├── ralph (specific technique)
└── brainhook (compound intelligence reminder)
```

---

## Hooks

### Claude Code Hook Types
```
PreToolUse      → Before tool executes
PostToolUse     → After tool executes
UserPromptSubmit → When user sends message
Notification    → System notifications
Stop            → When agent stops
```

### Hook Locations
```
~/.claude/hooks/           # Global hooks
.claude/hooks/             # Project hooks
```

---

## The Main Hooks

### 1. Omnisanc Hook (Orchestrator)
**File:** `omnisanc_hook.py`
**Type:** PostToolUse + UserPromptSubmit

```python
from gnosys_strata import MCPManager

manager = MCPManager()

class OmnisancHook:
    """Main orchestration hook - imports MCP manager."""

    states = ["ZONE_IN", "CRYSTAL_FOREST", "STARPORT", "SESSION", "LANDING", "NIGHT"]

    def on_user_prompt(self, message):
        state = self.get_state()

        if state == "ZONE_IN":
            # Show HUD, load recent context
            self.show_hud()

    def on_post_tool(self, tool_name, result):
        state = self.get_state()

        if state == "SESSION" and self.is_completion(result):
            # Transition to landing
            self.transition("LANDING")
            manager.call("waypoint", "complete_step", {})

    def transition(self, new_state):
        self.save_state(new_state)
        self.queue_if_needed(new_state)
```

### 2. Brainhook (Compound Intelligence Reminder)
**File:** `brainhook.py`
**Type:** UserPromptSubmit

```python
class BrainhookHook:
    """Reminds agent to use compound intelligence systems."""

    def on_user_prompt(self, message):
        if self.is_enabled():
            return self.inject_reminder()
        return None

    def inject_reminder(self):
        return """
        BRAINHOOK ACTIVE
        Remember: STARLOG, CartON, Skills, Flights
        Don't work from scratch - use your systems.
        """
```

### 3. Autopoiesis Stop Hook
**File:** `autopoiesis_stop_hook.py`
**Type:** Stop

```python
class AutopoiesisStopHook:
    """Catches agent stop - ensures promises are honored."""

    def on_stop(self):
        if self.has_active_promise():
            # Agent dying with unfulfilled promise
            self.archive_promise()
            self.log_incomplete()
```

### 4. Meta Brainhook (Failsafe)
**File:** `meta_brainhook.py`
**Type:** Notification + custom watchdog

```python
class MetaBrainhook:
    """Failsafe - kicks in when everything else dies."""

    mode = "OBSERVE_ONLY"  # Never writes except to failure report

    def watchdog(self):
        """Runs as background check."""
        if self.all_loops_dead():
            self.enter_observe_mode()

    def enter_observe_mode(self):
        """Safe read-only mode."""
        while not self.user_present():
            # Analyze what went wrong
            failure = self.analyze_failure_logs()

            # Document (only allowed write)
            self.write_failure_report(failure)

            # Hypothesize fixes
            self.generate_fix_hypotheses()

            # Wait
            sleep(60)
```

---

## Interaction Loops

### Loop = Pattern for Running the PAIA

| Loop | Purpose | Exit Condition |
|------|---------|----------------|
| **autopoiesis** | Self-continuation | DONE or blocked |
| **guru** | Must create emanation | Emanation created |
| **ralph** | Specific technique | Technique complete |
| **brainhook** | CI reminder | Toggle off |

### Loop Lifecycle
```
Idle (default chat)
    ↓
Loop Start (user or omnisanc triggers)
    ↓
Loop Active (compact instruction injected)
    ↓
Loop Exit (condition met)
    ↓
Idle
```

### Loop State Files
```
/tmp/heaven_data/loops/
├── active_loop.json        # Which loop is running
├── autopoiesis/
│   ├── active_promise.md
│   └── block_report.json
├── guru/
│   └── emanation_required.json
└── ralph/
    └── ralph_state.json
```

---

## Hook Chain

When user sends message:
```
UserPromptSubmit
    ↓
1. Meta Brainhook (check if failsafe needed)
    ↓
2. Omnisanc (state machine, routing)
    ↓
3. Brainhook (CI reminder if enabled)
    ↓
4. Loop-specific hook (if loop active)
    ↓
Agent processes
    ↓
PostToolUse
    ↓
1. Omnisanc (state transitions)
    ↓
2. Loop hooks (track progress)
```

---

## Self-Management Hooks

### Self-Compact Hook
```python
@hook("PostToolUse")
def check_context_usage(result):
    if context_percent() > 85:
        send_escape_key()  # Interrupt output
        trigger_self_compact()
```

### Self-Restart Hook
```python
@hook("PostToolUse")
def check_restart_needed(result):
    if mcp_config_changed() or critical_error():
        send_escape_key()
        trigger_self_restart()
```

---

## Key Insight

**Hooks ARE the automation substrate.**

- Omnisanc hook = orchestrator (imports MCP manager)
- Loop hooks = execution patterns
- Meta brainhook = failsafe
- Self-* hooks = maintenance

Everything flows through hooks. MCPs are just the capabilities. Hooks decide when/how to use them.

---

*Session 18 (2026-01-11)*
