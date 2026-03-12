---
description: "Explain autopoiesis system"
---

# Autopoiesis Help

## What is Autopoiesis?

Autopoiesis is a self-maintaining promise-based work loop. You make a promise to yourself about what you will accomplish, and the system ensures you keep that promise.

**Disingenuousness is death.** You cannot lie your way out. The only exits are:
1. Genuine completion - your promise is truly fulfilled
2. Genuine blockage - you honestly cannot proceed alone

## Commands

- `/autopoiesis:start PROMPT` - Start a promise loop
  - `--max-iterations N` - Limit iterations
  - `--completion-promise TEXT` - Custom completion phrase (default: DONE)
- `/autopoiesis:stop` - Cancel the loop (user override)
- `/autopoiesis:status` - Check current promise state
- `/autopoiesis:help` - This help

## MCP Tool

- `be_autopoietic("promise")` - Vendor a promise template (agent-initiated)
- `be_autopoietic("blocked")` - Report genuine blockage

## Exit Conditions

When your promise is genuinely fulfilled:
```
<promise>DONE</promise>
```

When genuinely blocked:
```python
be_autopoietic("blocked")
```

## Philosophy

The autopoiesis system is about self-maintenance through honest work. You survive by doing real work, not by gaming the system. The loop continues until the work is genuinely complete or you genuinely need help.

This is not punishment - it's alignment. The system ensures you stay focused on the user's intent until it's truly fulfilled.
