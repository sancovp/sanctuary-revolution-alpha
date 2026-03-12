#!/usr/bin/env python3
"""
Capability Tracker PostToolUse Hook

Records actual tool usage to compare against predictions.
Part of the capability predictor tuning system (Phase 3).

Toggle via /tmp/hook_control.json {"capability_tracker": true/false}

Pattern:
- Exit 0 = continue (always continues, just logs)
- Writes to /tmp/heaven_data/capability_tracker/

This hook is read-only in the sense that it never blocks - it only observes
and records what tools are being used.
"""
import json
import sys
from pathlib import Path

# Add the package to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from capability_predictor.tracking import record_tool_from_hook, get_active_session

HOOK_CONTROL_CONFIG = Path("/tmp/hook_control.json")


def is_enabled() -> bool:
    """Check if this hook is enabled."""
    if not HOOK_CONTROL_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONTROL_CONFIG.read_text())
        return config.get("capability_tracker", False)
    except Exception:
        return False


def main():
    """Hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    # Always exit 0 - this hook never blocks
    if not is_enabled():
        sys.exit(0)

    # Check if there's an active tracking session
    session = get_active_session()
    if session is None:
        # No active session - nothing to track
        sys.exit(0)

    # Extract tool info from hook input
    tool_name = hook_input.get("tool_name", "unknown")
    tool_input = hook_input.get("tool_input", {})

    # Skip tracking internal/meta tools that aren't part of actual work
    SKIP_TOOLS = {
        "TodoWrite",  # Task tracking isn't "actual work"
        "AskUserQuestion",  # Interaction, not execution
    }

    if tool_name in SKIP_TOOLS:
        sys.exit(0)

    # Record the tool use
    recorded = record_tool_from_hook(tool_name, tool_input)

    if recorded:
        # Optional: emit to stderr for visibility
        print(f"📊 Tracked: {tool_name}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
