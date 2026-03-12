#!/usr/bin/env python3
"""
PreToolUse hook that enforces be_myself must be called first each turn.

Writes a flag file when be_myself is called, blocks all other tools if flag doesn't exist.
The stop hook deletes the flag at end of turn.

Uses strata_unwrap to handle TreeShell-wrapped and Strata-wrapped calls.

Hook protocol:
- Input: JSON via stdin (not env var)
- Allow: exit(0)
- Block: exit(2) with message on stderr
"""

import os
import sys
import json
import logging
from pathlib import Path

from strata_unwrap import get_actual_tool_name

# Logging to stderr (stdout is for hook protocol)
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("BE_MYSELF_DEBUG") else logging.WARNING,
    format="[be_myself] %(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

CONTINUITY_FILE = Path(os.environ.get("SELF_CONTINUITY_PATH", "/tmp/self_continuity.log"))

# Tools that are always allowed (never block these)
# These are the UNWRAPPED tool names
ALWAYS_ALLOWED = {
    # be_myself variants (direct and via GIINT)
    "core__be_myself",
    "mcp__giint-llm-intelligence__core__be_myself",
    # TreeShell wrappers themselves (when not executing an action)
    "mcp__gnosys_kit__run_conversation_shell",
    "mcp__skill_manager_treeshell__run_conversation_shell",
}


def main():
    # Read from stdin (Claude Code hook protocol)
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No input = pass through
        sys.exit(0)

    raw_tool_name = hook_input.get("tool_name", "")

    # Unwrap TreeShell/Strata calls to get actual tool name
    actual_tool_name = get_actual_tool_name(hook_input)
    logger.debug(f"raw={raw_tool_name} actual={actual_tool_name}")

    # be_myself variants are always allowed and set the flag
    if actual_tool_name in ALWAYS_ALLOWED or "be_myself" in actual_tool_name:
        logger.debug(f"Allowing and setting flag: {actual_tool_name}")
        CONTINUITY_FILE.write_text("YES")
        sys.exit(0)  # Allow

    # Any other tool - check if be_myself was called this turn
    if CONTINUITY_FILE.exists():
        logger.debug(f"Flag exists, allowing: {actual_tool_name}")
        sys.exit(0)  # Allow
    else:
        # Block with message on stderr
        logger.warning(f"Blocking - no be_myself flag: {actual_tool_name}")
        sys.stderr.write(f"🧘 Must be_myself first. Tried: {actual_tool_name}. Call mcp__giint-llm-intelligence__core__be_myself() or use gnosys_kit to call be_myself.\n")
        sys.exit(2)  # Block


if __name__ == "__main__":
    main()
