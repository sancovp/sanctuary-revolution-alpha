---
description: "Start isolated Ralph loop using ralph-orchestrator SDK"
argument-hint: "--prompt-file PROMPT.md [--max-iterations N]"
---

# Isolated Ralph Loop

Runs ralph-orchestrator with Claude SDK for proper isolated subprocess work.

**Run:**
```bash
"$CLAUDE_PLUGIN_ROOT/scripts/isolated-ralph-loop.sh" $ARGUMENTS
```

## Examples

```bash
/ralph-isolated --prompt-file PROMPT.md --max-iterations 10
/ralph-isolated --prompt-file /path/to/task.md
```

See `ralph --help` for all options.
