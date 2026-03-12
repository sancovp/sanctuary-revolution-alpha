#!/usr/bin/env python3
"""PAIA Stop hook - intercepts when Claude Code stops.

Toggle via /tmp/hook_config.json {"stop": true/false}
"""
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOOK_CONFIG = Path("/tmp/hook_config.json")
STOP_LOG = Path("/tmp/paia_hooks/stop_events.jsonl")


def is_enabled() -> bool:
    """Check if this hook is enabled."""
    if not HOOK_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONFIG.read_text())
        return config.get("stop", False)
    except Exception:
        logger.error(f"Failed to read hook config: {traceback.format_exc()}")
        return False


def main():
    """Hook entry point."""
    hook_input = json.loads(sys.stdin.read())

    if not is_enabled():
        return

    # Log stop event for harness visibility
    STOP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with STOP_LOG.open("a") as f:
        f.write(json.dumps({
            "reason": hook_input.get("reason", "unknown"),
            "stop_hook_active": True
        }) + "\n")


if __name__ == "__main__":
    main()
