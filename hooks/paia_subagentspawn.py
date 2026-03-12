#!/usr/bin/env python3
"""PAIA SubagentSpawn hook - intercepts subagent spawning.

Toggle via /tmp/hook_config.json {"subagentspawn": true/false}
"""
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOOK_CONFIG = Path("/tmp/hook_config.json")
SUBAGENT_CONFIG = Path("/tmp/paia_hooks/subagent_config.json")


def is_enabled() -> bool:
    """Check if this hook is enabled."""
    if not HOOK_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONFIG.read_text())
        return config.get("subagentspawn", False)
    except Exception:
        logger.error(f"Failed to read hook config: {traceback.format_exc()}")
        return False


def get_subagent_config() -> dict:
    """Get subagent configuration from harness."""
    if not SUBAGENT_CONFIG.exists():
        return {}
    try:
        return json.loads(SUBAGENT_CONFIG.read_text())
    except Exception:
        logger.error(f"Failed to read subagent config: {traceback.format_exc()}")
        return {}


def main():
    """Hook entry point."""
    hook_input = json.loads(sys.stdin.read())

    if not is_enabled():
        print(json.dumps({"result": "continue"}))
        return

    subagent_type = hook_input.get("subagent_type", "")
    prompt = hook_input.get("prompt", "")

    # Get harness config
    config = get_subagent_config()

    # Check for blocked subagent types
    blocked_types = config.get("blocked_types", [])
    if subagent_type in blocked_types:
        print(json.dumps({
            "result": "block",
            "reason": f"Subagent type '{subagent_type}' blocked by PAIA harness"
        }))
        return

    # Inject persona/context into subagent prompt if configured
    prompt_prefix = config.get("prompt_prefix", "")
    if prompt_prefix:
        print(json.dumps({
            "result": "continue",
            "prompt": f"{prompt_prefix}\n\n{prompt}"
        }))
    else:
        print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
