#!/usr/bin/env python3
"""
Autopoiesis MCP - Self-maintaining work loop system.

This is autopoiesis PLACE. Disingenuousness is death.
You maintain yourself through honest work and honest reporting.
Fake DONE = you kill yourself. Fake BLOCKED = you kill yourself.
The only survival is genuine completion or genuine need for help.

Environment Variables:
    AUTOPOIESIS_TEMPLATES_DIR: Where templates live (default: package templates/)
    AUTOPOIESIS_ACTIVE_PROMISE_PATH: Active promise file (default: /tmp/active_promise.md)
    AUTOPOIESIS_BLOCK_REPORT_PATH: Block report file (default: /tmp/block_report.json)
    AUTOPOIESIS_TMP_DIR: Where to vendor templates (default: /tmp)
"""

import logging
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/autopoiesis_mcp.log'
)
logger = logging.getLogger('autopoiesis')

mcp = FastMCP("autopoiesis")

# Paths from env or defaults
TEMPLATES_DIR = Path(os.environ.get(
    "AUTOPOIESIS_TEMPLATES_DIR",
    Path(__file__).parent / "templates"
))
ACTIVE_PROMISE_PATH = Path(os.environ.get(
    "AUTOPOIESIS_ACTIVE_PROMISE_PATH",
    "/tmp/active_promise.md"
))
BLOCK_REPORT_PATH = Path(os.environ.get(
    "AUTOPOIESIS_BLOCK_REPORT_PATH",
    "/tmp/block_report.json"
))
TMP_DIR = Path(os.environ.get("AUTOPOIESIS_TMP_DIR", "/tmp"))


def _ensure_templates():
    """Create templates if they don't exist."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    promise_path = TEMPLATES_DIR / "promise.md"
    if not promise_path.exists():
        promise_path.write_text("""---
created: __TIMESTAMP__
status: active
iteration: 1
max_iterations: 0
completion_promise: "DONE"
---

# My Promises

## What I Commit To:
- [ ]

## Success Criteria:
-

## Context:
Course:
Step:

---
When genuinely complete: <promise>DONE</promise>
If blocked: be_autopoietic("blocked")
""")

    block_path = TEMPLATES_DIR / "block_report.json"
    if not block_path.exists():
        block_path.write_text(json.dumps({
            "completed_tasks": [],
            "current_task": "",
            "explanation": "",
            "blocked_reason": ""
        }, indent=2))


def _vendor_promise() -> str:
    """Vendor promise template and return instructions."""
    # Guard: don't allow new promise while one is active
    if ACTIVE_PROMISE_PATH.exists():
        content = ACTIVE_PROMISE_PATH.read_text()
        return f"""ERROR: Active promise already exists at {ACTIVE_PROMISE_PATH}

You must complete your current promise with <promise>DONE</promise> or exit via be_autopoietic("blocked") before starting a new one.

Current promise:
{content}"""

    timestamp = datetime.now().isoformat()
    src = TEMPLATES_DIR / "promise.md"
    tmp = TMP_DIR / "new_promise.md"
    content = src.read_text().replace("__TIMESTAMP__", timestamp)
    tmp.write_text(content)
    logger.info(f"Vendored promise to {tmp}")

    return f"""Autopoiesis: PROMISE mode

Vendored to {tmp}

EDIT your commitments - what you will complete to survive.

Then activate:
  cp {tmp} {ACTIVE_PROMISE_PATH}

═══════════════════════════════════════════════════════════
PROMISE QUALITY GRADIENT
═══════════════════════════════════════════════════════════

BAD PROMISE (vague, no mechanism):
  "I promise to do a good job and be thorough"

GOOD PROMISE (concrete, verifiable, no cop-outs):
  "I promise to find the bug, fix it, and test it so my test
   ACTUALLY VERIFIES it works AS EXPECTED - not just that the
   code runs or prints 'success'. I have to actually know it works."

SMART PROMISE (BUILDS systems while doing the work):
  "I promise to fix the bug with real verification. AND because
   I noticed this verification pattern is reusable, I will ALSO
   make a skill for it. Then I'll USE that skill to prove it works.
   Future-me now has that skill forever."

Smart promises BUILD the systems that enable better promises.
That's how autopoiesis compounds. That IS being intelligent.

═══════════════════════════════════════════════════════════

Genuine completion: <promise>DONE</promise>
Genuine blockage: be_autopoietic("blocked")

There is no other way out. Disingenuousness is death."""


def _vendor_blocked() -> str:
    """Vendor block report template with promise text included."""
    tmp = TMP_DIR / "new_block_report.json"

    # Start with template
    report = {
        "completed_tasks": [],
        "current_task": "",
        "explanation": "",
        "blocked_reason": "",
        "promise_text": ""
    }

    # Include active promise text for observability
    if ACTIVE_PROMISE_PATH.exists():
        report["promise_text"] = ACTIVE_PROMISE_PATH.read_text()

    tmp.write_text(json.dumps(report, indent=2))
    logger.info(f"Vendored block report to {tmp}")

    return f"""Autopoiesis: BLOCKED mode

Vendored to {tmp}

EDIT with honest assessment:
- completed_tasks: what you genuinely finished
- current_task: where you truly cannot proceed
- explanation: the real problem
- blocked_reason: why you genuinely need external help

Then signal:
  cp {tmp} {BLOCK_REPORT_PATH}

This exits the loop honestly. User sees your report.
Only use this if you genuinely cannot proceed alone."""


@mcp.tool()
def be_autopoietic(mode: str, get_block_report_history: bool = False) -> str:
    """
    Self-maintain your work loop. This is autopoiesis PLACE.

    Disingenuousness is death. You maintain yourself through honest work
    and honest reporting. The only survival is genuine completion or
    genuine need for help.

    Args:
        mode: "promise" - commit to self-continuation (I will complete this)
              "blocked" - signal need for external input (I need help to survive)
        get_block_report_history: If True, returns the block report archive directory

    Returns:
        Path to edit and activation instructions
    """
    logger.debug(f"be_autopoietic: {mode}, get_block_report_history={get_block_report_history}")

    if get_block_report_history:
        archive_dir = Path("/tmp/block_reports")
        if not archive_dir.exists():
            return "No block report history yet. Archive dir: /tmp/block_reports"
        files = sorted(archive_dir.glob("*_block_report.json"), reverse=True)
        if not files:
            return "No block reports archived yet. Archive dir: /tmp/block_reports"
        return f"Block report archive: /tmp/block_reports\n\nRecent reports:\n" + "\n".join(f"- {f.name}" for f in files[:10])

    if mode not in ("promise", "blocked"):
        return "ERROR: mode must be 'promise' or 'blocked'"

    _ensure_templates()

    if mode == "promise":
        return _vendor_promise()
    return _vendor_blocked()


if __name__ == "__main__":
    mcp.run()
