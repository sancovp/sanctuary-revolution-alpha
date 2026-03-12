#!/usr/bin/env python3
"""
PAIA Injection Hook - Reads pending injections from harness and injects into context.

Watches /tmp/paia_hooks/pending_injection.json for events from:
- Psyche (internal state changes)
- World (external events)
- System (infrastructure)

Injects as system-reminder tags in Claude Code context.

Toggle via /tmp/hook_config.json {"userpromptsubmit": true/false}
"""
import json
import logging
import sys
import traceback
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOOK_CONFIG = Path("/tmp/hook_config.json")
INJECTION_FILE = Path("/tmp/paia_hooks/pending_injection.json")
PROCESSED_FILE = Path("/tmp/paia_hooks/processed_injections.json")
PERSONA_FLAG = Path("/tmp/active_persona")


def is_enabled() -> bool:
    """Check if this hook is enabled via config."""
    if not HOOK_CONFIG.exists():
        return False
    try:
        config = json.loads(HOOK_CONFIG.read_text())
        return config.get("userpromptsubmit", False)
    except Exception:
        logger.error(f"Failed to read hook config: {traceback.format_exc()}")
        return False


def get_active_persona() -> str | None:
    """Get active persona name if any."""
    if PERSONA_FLAG.exists():
        name = PERSONA_FLAG.read_text().strip()
        return name if name else None
    return None


def get_pending_injections() -> list[dict]:
    """Read and clear pending injections."""
    if not INJECTION_FILE.exists():
        return []

    try:
        pending = json.loads(INJECTION_FILE.read_text())
        if not pending:
            return []

        # Mark as processed
        processed = []
        if PROCESSED_FILE.exists():
            try:
                processed = json.loads(PROCESSED_FILE.read_text())
            except Exception:
                logger.error(f"Failed to read processed file: {traceback.format_exc()}")
                processed = []

        processed.extend(pending)
        processed = processed[-50:]  # Keep last 50
        PROCESSED_FILE.write_text(json.dumps(processed, indent=2))

        # Clear pending
        INJECTION_FILE.write_text("[]")

        return pending

    except Exception:
        logger.error(f"Error reading injections: {traceback.format_exc()}")
        return []


def format_injection(inj: dict) -> str:
    """Format injection for Claude Code context."""
    source = inj.get("source", "unknown")
    event = inj.get("event", "event")
    message = inj.get("message", "")
    priority = inj.get("priority", 5)

    # Icon based on source
    icons = {
        "psyche": "🧠",
        "world": "🌍",
        "system": "⚙️",
    }
    icon = icons.get(source, "•")

    # Priority marker
    priority_marker = "!" * min(priority // 3, 3) if priority > 5 else ""

    return f"[{icon} {source.upper()}/{event}]{priority_marker} {message}"


def main():
    """Hook entry point."""
    # Read hook input (required even if not used)
    _ = json.loads(sys.stdin.read())

    # Check if hook is enabled
    if not is_enabled():
        print(json.dumps({"result": "continue"}))
        return

    messages = []

    # Check for active persona
    persona = get_active_persona()
    if persona:
        messages.append(f"[PERSONA ACTIVE: {persona}]")

    # Get pending injections
    injections = get_pending_injections()
    for inj in injections:
        messages.append(format_injection(inj))

    if not messages:
        print(json.dumps({"result": "continue"}))
        return

    # Output as system reminder addition
    combined = "\n".join(messages)
    print(json.dumps({
        "result": "continue",
        "additionalContext": f"PAIA Harness:\n{combined}"
    }))


if __name__ == "__main__":
    main()
