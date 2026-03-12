# MetaBrainHook Toggle

Toggle orchestration mode on/off.

When ON, every prompt gets injected with:
- Allowed directories (sandbox)
- Current situation info
- Goal
- Task queue
- Reminders (positive reinforcement)
- Guru activation instructions

Config file: `/tmp/heaven_data/metabrainhook_config.json`
Edit this file to steer the agent remotely.

## Usage

Toggle: `/metabrainhook` or `metabrainhook` in bash

## To steer the agent:

1. Turn on: `metabrainhook on` (or `/metabrainhook`)
2. Edit config: `nano /tmp/heaven_data/metabrainhook_config.json`
3. Agent picks up changes on next prompt

## Config fields:

```json
{
  "allowed_dirs": ["/path/to/project"],
  "info": "Context about current situation",
  "goal": "What to accomplish",
  "reminders": ["Stay focused", "Use starlog"],
  "queue": ["Task 1", "Task 2"],
  "guru_instructions": "How to activate guru loop"
}
```

---

$ARGUMENTS: on|off (optional, toggles if not provided)

```bash
#!/bin/bash
STATE_FILE="/tmp/metabrainhook_state.txt"

if [ "$1" = "on" ]; then
    echo "on" > "$STATE_FILE"
    echo "MetaBrainHook ON - orchestration mode active"
elif [ "$1" = "off" ]; then
    echo "off" > "$STATE_FILE"
    echo "MetaBrainHook OFF"
else
    # Toggle
    if [ -f "$STATE_FILE" ] && [ "$(cat $STATE_FILE)" = "on" ]; then
        echo "off" > "$STATE_FILE"
        echo "MetaBrainHook OFF"
    else
        echo "on" > "$STATE_FILE"
        echo "MetaBrainHook ON - orchestration mode active"
    fi
fi
```
