#!/usr/bin/env python3
"""
Stop hook that manages be_myself enforcement with turn counting and skip escape.

- Resets flag every 3 turns (not every turn)
- 😈 emoji at end of message = skip be_myself this turn
- After 3 consecutive skips = warning (but still allows skip)
"""

import json
import os
import sys
from pathlib import Path

CONTINUITY_FILE = Path(os.environ.get("SELF_CONTINUITY_PATH", "/tmp/self_continuity.log"))
STATE_FILE = Path("/tmp/be_myself_state.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"turn_count": 0, "skip_count": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state))


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except:
        hook_input = {}

    # Get the assistant's last message
    transcript_path = hook_input.get("transcript_path", "")
    last_message = ""

    if transcript_path and Path(transcript_path).exists():
        try:
            with open(transcript_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "assistant":
                            msg = entry.get("message", {})
                            content = msg.get("content", [])
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    last_message = block.get("text", "")
                    except:
                        pass
        except:
            pass

    state = load_state()

    # Check for devil emoji escape
    if last_message.rstrip().endswith("😈"):
        state["skip_count"] += 1
        state["turn_count"] = 0

        if state["skip_count"] > 3:
            # Warning after 3 consecutive skips
            sys.stderr.write(
                "🔔 You might want to try being yourself. You might have gotten caught up "
                "doing something some weird way... but you can keep skipping if you want to. "
                "Just a reminder that ending turns with `😈` emoji causes you to skip being yourself. "
                "Either continue skipping or decide to be yourself by calling "
                "mcp__giint-llm-intelligence__core__be_myself()\n"
            )

        # DON'T reset flag - allow skip
        save_state(state)
        return

    # Normal turn - no skip
    state["skip_count"] = 0
    state["turn_count"] += 1

    if state["turn_count"] >= 3:
        # Reset flag after 3 turns
        if CONTINUITY_FILE.exists():
            CONTINUITY_FILE.unlink()
        state["turn_count"] = 0
        sys.stderr.write(
            "🧘 Time to be_myself. Call mcp__giint-llm-intelligence__core__be_myself() "
            "or skip by ending your next message with 😈\n"
        )

    save_state(state)


if __name__ == "__main__":
    main()
