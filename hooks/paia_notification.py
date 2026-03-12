#!/usr/bin/env python3
"""PAIA Notification hook - intercepts Claude Code notifications.

Toggle via /tmp/hook_config.json {"notification": true/false}
"""
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOOK_CONFIG = Path("/tmp/hook_config.json")
NOTIFICATION_LOG = Path("/tmp/paia_hooks/notifications.jsonl")


def is_enabled() -> bool:
    """Check if this hook is enabled."""
    if not HOOK_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONFIG.read_text())
        return config.get("notification", False)
    except Exception:
        logger.error(f"Failed to read hook config: {traceback.format_exc()}")
        return False


def main():
    """Hook entry point."""
    hook_input = json.loads(sys.stdin.read())

    if not is_enabled():
        return

    # Log notification for harness visibility
    NOTIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with NOTIFICATION_LOG.open("a") as f:
        f.write(json.dumps(hook_input) + "\n")


if __name__ == "__main__":
    main()
