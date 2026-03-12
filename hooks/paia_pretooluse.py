#!/usr/bin/env python3
"""PAIA PreToolUse hook - intercepts before tool execution.

Toggle via /tmp/hook_config.json {"pretooluse": true/false}
"""
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOOK_CONFIG = Path("/tmp/hook_config.json")
PRETOOL_CONFIG = Path("/tmp/paia_hooks/pretool_config.json")


def is_enabled() -> bool:
    """Check if this hook is enabled."""
    if not HOOK_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONFIG.read_text())
        return config.get("pretooluse", False)
    except Exception:
        logger.error(f"Failed to read hook config: {traceback.format_exc()}")
        return False


def get_pretool_config() -> dict:
    """Get any pretool configuration from harness."""
    if not PRETOOL_CONFIG.exists():
        return {}
    try:
        return json.loads(PRETOOL_CONFIG.read_text())
    except Exception:
        logger.error(f"Failed to read pretool config: {traceback.format_exc()}")
        return {}


def main():
    """Hook entry point."""
    hook_input = json.loads(sys.stdin.read())

    if not is_enabled():
        print(json.dumps({"result": "continue"}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Get harness config for any tool-specific rules
    config = get_pretool_config()

    # Check for blocked tools
    blocked_tools = config.get("blocked_tools", [])
    if tool_name in blocked_tools:
        print(json.dumps({
            "result": "block",
            "reason": f"Tool '{tool_name}' blocked by PAIA harness"
        }))
        return

    # Check for tool modifications
    modifications = config.get("tool_modifications", {})
    if tool_name in modifications:
        mod = modifications[tool_name]
        # Could modify tool_input here based on mod rules
        pass

    # Pass through with optional context
    context = config.get("context_injection", "")
    if context:
        print(json.dumps({
            "result": "continue",
            "additionalContext": f"[PAIA PreTool] {context}"
        }))
    else:
        print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
