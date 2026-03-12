---
description: "Start autopoiesis loop in current session"
argument-hint: "PROMPT [--max-iterations N] [--completion-promise TEXT]"
---

# Autopoiesis

You are in the autopoiesis system. This requires making and keeping promises to yourself.

**Run this command to initialize the loop:**

```
"$CLAUDE_PLUGIN_ROOT/scripts/setup-autopoiesis.sh" $ARGUMENTS
```

After running the script, read `/tmp/active_promise.md` to see the active promise.

## Rules

1. Work on the task specified in the arguments
2. When you try to exit, the stop hook will check if you kept your promise
3. If a completion promise is set, you may ONLY say `<promise>DONE</promise>` (or whatever the promise text is) when it is completely and unequivocally TRUE
4. Do not output false promises to escape the loop

## If Blocked

If you are genuinely blocked and cannot continue, use `be_autopoietic("blocked")` to exit honestly. Disingenuousness is death.
