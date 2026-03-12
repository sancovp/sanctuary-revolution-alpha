#!/usr/bin/env python3
# codenose ignore
"""
Context Inject Hook - Inject context percentage on PostToolUse

Reads from /tmp/context_percent.txt (written by statusline) and injects
"ContextWindow: N%" into tool results so Claude sees context pressure.
"""

import json
import sys
import traceback

# NOTE: Hook scripts use print() to stdout for Claude Code protocol communication
# This is intentional - not a code smell. stderr is used for debug logging.

CONTEXT_PERCENT_FILE = "/tmp/context_percent.txt"


def get_context_percent() -> int | None:
    """Read context percentage from file."""
    try:
        with open(CONTEXT_PERCENT_FILE, 'r') as f:
            percent = f.read().strip()
            if percent.isdigit():
                return int(percent)
    except FileNotFoundError:
        pass
    except Exception as e:
        sys.stderr.write(f"context_inject_hook error: {e}\n{traceback.format_exc()}")
    return None


HANDOFF_FILE = "/tmp/claude_handoff.md"


def get_context_message(percent: int) -> str:
    """Get tiered context warning message."""
    if percent >= 98:
        return (
            f"ContextWindow: {percent}%\n"
            f"═══════════════════════════════════════════════════════════\n"
            f"🚀 CLASP PROTOCOL - YOU ARE THE BROADCASTER\n"
            f"═══════════════════════════════════════════════════════════\n\n"
            f"Context is critical. You must hand off to your future self.\n\n"
            f"STEP 1: WRITE THE HANDOFF FILE\n"
            f"   Path: {HANDOFF_FILE}\n"
            f"   Include: Current task, key state, what's unfinished, next steps\n\n"
            f"STEP 2: BROADCAST UNTIL COMPACTION\n"
            f"   Emit this in EVERY response: <clasp>BROADCASTING handoff at {HANDOFF_FILE}</clasp>\n"
            f"   Keep working and broadcasting - compaction will happen automatically\n\n"
            f"STEP 3: COMPACTION HAPPENS (automatic)\n"
            f"   Your context gets summarized, a new Claude instance starts\n\n"
            f"WHAT HAPPENS NEXT (for your future self):\n"
            f"   - New Claude will be BLOCKED until they acknowledge\n"
            f"   - They read {HANDOFF_FILE}\n"
            f"   - They respond with <clasp>RECEIVED</clasp>\n"
            f"   - Handoff file is deleted, continuity restored"
        )
    elif percent >= 92:
        return f"ContextWindow: {percent}% 🔥 HOT - Wind down current task. Start organizing handoff notes."
    elif percent >= 82:
        return f"ContextWindow: {percent}% ⚠️ WARMING - Consider wrapping current task soon."
    else:
        return f"ContextWindow: {percent}%"


def main():
    try:
        # Read hook input (not used, but required)
        hook_data = json.load(sys.stdin)

        # Get context percent
        percent = get_context_percent()

        if percent is not None:
            # Inject context info with tiered warning
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": get_context_message(percent)
                }
            }
        else:
            # No context info available, pass through
            result = {}

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"context_inject_hook error: {e}\n{traceback.format_exc()}")
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
