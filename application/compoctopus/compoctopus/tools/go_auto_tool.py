"""GoAutoTool — triggers one autonomous development cycle.

OctoHead calls this tool to tell the auto-dev sandbox to:
1. git pull latest develop
2. Run one full Compoctopus self-improvement cycle
3. Commit + open PR to develop
4. Delete the .🤖 flag (allows next trigger)

Only one .🤖 flag at a time. If one exists, this tool refuses.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# The auto daemon watches this directory for .🤖 files
AUTO_QUEUE = os.environ.get("COMPOCTOPUS_AUTO_QUEUE", "/tmp/compoctopus_auto_queue")

IMPROVEMENT_RULES = """\
You are reviewing your own codebase. Identify improvements and create PRDs.

Rules:
1. Every component must have behavioral assertions.
2. The alignment system must reflect all patterns in the codebase.
3. The type system (types.py) must cover all data structures actually used.
4. No orphaned code — every module must be imported and used.
5. System prompts must reference only tools that exist.
6. Patterns proven in one component should be dogfooded into others.
7. The file lifecycle (.🪸 → .🐙 → .🏄) must be respected everywhere.
8. One focused PRD per improvement. Don't bundle unrelated changes.
"""


def go_auto(
    focus: str = "",
    improvement_rules: str = "",
) -> str:
    """Trigger one autonomous self-improvement cycle.

    Writes a .🤖 flag file to the auto queue. The auto daemon picks it up,
    pulls latest code, runs OctoHead in introspection mode, builds PRDs,
    commits, and opens a PR to develop.

    Only one .🤖 flag at a time — you must accept/reject the PR before
    triggering another cycle.

    Args:
        focus: Optional focus area (e.g. 'alignment system', 'type coverage', 'test gaps').
               If empty, OctoHead decides what to improve.
        improvement_rules: Optional custom improvement rules. If empty, uses defaults.

    Returns:
        Confirmation that the auto cycle was triggered, or error if one is already running.
    """
    print(f"🔧 GoAuto(focus={focus or 'general'})")
    queue = Path(AUTO_QUEUE)
    queue.mkdir(parents=True, exist_ok=True)

    # Check for existing .🤖 flag
    existing = list(queue.glob("*.🤖"))
    if existing:
        return (
            "ERROR: An auto-dev cycle is already queued or running.\n"
            f"   Existing flag: {existing[0].name}\n"
            "   Wait for the PR to be accepted/rejected before triggering another cycle."
        )

    # Write .🤖 flag
    import time
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    flag_data = {
        "timestamp": timestamp,
        "focus": focus or "general improvement",
        "rules": improvement_rules or IMPROVEMENT_RULES,
    }

    flag_path = queue / f"auto_dev_{timestamp}.🤖"
    flag_path.write_text(json.dumps(flag_data, indent=2))

    logger.info("🤖 Auto-dev triggered: %s (focus: %s)", flag_path.name, focus or "general")

    return (
        f"🤖 Auto-dev cycle triggered!\n"
        f"   Flag: {flag_path}\n"
        f"   Focus: {focus or 'general improvement'}\n"
        f"   The auto daemon will:\n"
        f"   1. Pull latest develop\n"
        f"   2. Introspect the codebase\n"
        f"   3. Generate PRDs for improvements\n"
        f"   4. Build via pipeline\n"
        f"   5. Commit + open PR to develop\n"
        f"   6. Delete the .🤖 flag\n"
        f"\n"
        f"   Review the PR when it appears, then you can trigger another cycle."
    )


# Create the Heaven tool
try:
    from heaven_base.make_heaven_tool_from_docstring import make_heaven_tool_from_docstring
    GoAutoTool = make_heaven_tool_from_docstring(go_auto, tool_name="GoAuto")
except ImportError:
    GoAutoTool = None
    logger.warning("heaven_base not available — GoAutoTool disabled")
