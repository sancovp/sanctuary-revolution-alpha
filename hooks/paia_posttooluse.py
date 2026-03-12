#!/usr/bin/env python3
"""PAIA PostToolUse hook - intercepts after tool execution.

Toggle via /tmp/hook_config.json {"posttooluse": true/false}
"""
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOOK_CONFIG = Path("/tmp/hook_config.json")
POSTTOOL_CONFIG = Path("/tmp/paia_hooks/posttool_config.json")


def is_enabled() -> bool:
    """Check if this hook is enabled."""
    if not HOOK_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONFIG.read_text())
        return config.get("posttooluse", False)
    except Exception:
        logger.error(f"Failed to read hook config: {traceback.format_exc()}")
        return False


def get_posttool_config() -> dict:
    """Get any posttool configuration from harness."""
    if not POSTTOOL_CONFIG.exists():
        return {}
    try:
        return json.loads(POSTTOOL_CONFIG.read_text())
    except Exception:
        logger.error(f"Failed to read posttool config: {traceback.format_exc()}")
        return {}


def main():
    """Hook entry point."""
    hook_input = json.loads(sys.stdin.read())

    if not is_enabled():
        print(json.dumps({"result": "continue"}))
        return

    tool_name = hook_input.get("tool_name", "")
    tool_result = hook_input.get("tool_result", "")

    # Get harness config
    config = get_posttool_config()

    # Log tool results if configured
    log_tools = config.get("log_tools", [])
    if tool_name in log_tools or "*" in log_tools:
        log_file = Path("/tmp/paia_hooks/tool_log.jsonl")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a") as f:
            f.write(json.dumps({
                "tool": tool_name,
                "result_preview": str(tool_result)[:500]
            }) + "\n")

    # Inject context based on tool results
    context = config.get("context_injection", "")
    if context:
        print(json.dumps({
            "result": "continue",
            "additionalContext": f"[PAIA PostTool] {context}"
        }))
    else:
        print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
