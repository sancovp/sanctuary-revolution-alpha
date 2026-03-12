#!/usr/bin/env python3
"""Auto-Dev Loop — Compoctopus continuous self-improvement.

This script runs in the container and:
1. Pulls latest from develop
2. Runs OctoHead in autonomous mode (introspect + generate PRDs)
3. Daemon builds the PRDs
4. Commits output to a feature branch
5. Opens PR to develop via gh CLI
6. Cleans workspace
7. Loops

Usage:
    python auto_dev.py                    # single cycle
    python auto_dev.py --loop             # continuous loop
    python auto_dev.py --loop --interval 3600  # loop every hour
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(message)s')
logger = logging.getLogger("auto-dev")

REPO_URL = "https://github.com/sancovp/compoctopus.git"
WORKSPACE = "/tmp/compoctopus_autodev"
DAEMON_QUEUE = "/tmp/compoctopus_daemon_queue"

# Improvement rules OctoHead uses to introspect
IMPROVEMENT_RULES = """\
You are reviewing your own codebase. Your job is to identify improvements and create PRDs for them.

## Rules
1. Every component must have behavioral assertions (tests that prove it works).
2. The alignment system must reflect all patterns used in the codebase.
3. The type system (types.py) must cover all data structures actually used.
4. No orphaned code — every module must be imported and used somewhere.
5. System prompts must reference only tools that exist.
6. Patterns proven in one component should be dogfooded into others.
7. The file lifecycle (.🪸 → .🐙 → .🏄) must be respected everywhere.
8. Prefer one focused PRD per improvement. Don't bundle unrelated changes.

## What to look for
- Missing behavioral assertions
- Types used but not defined in types.py
- Patterns that work in one place but aren't applied elsewhere
- Code that could be simplified or unified
- Documentation gaps
- Alignment violations (tools referenced but not defined, etc.)
"""


def run_cmd(cmd: str, cwd: str = WORKSPACE) -> str:
    """Run shell command, return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Command failed: %s\n%s", cmd, result.stderr)
    return result.stdout.strip()


def pull_latest():
    """Clone or pull latest develop branch."""
    ws = Path(WORKSPACE)
    if (ws / ".git").exists():
        run_cmd("git checkout develop && git pull origin develop")
        logger.info("Pulled latest develop")
    else:
        ws.mkdir(parents=True, exist_ok=True)
        run_cmd(f"git clone {REPO_URL} {WORKSPACE}", cwd="/tmp")
        run_cmd("git checkout develop")
        logger.info("Cloned repo, on develop")


async def run_octohead_autonomous():
    """Run OctoHead in autonomous introspection mode."""
    sys.path.insert(0, WORKSPACE)

    from compoctopus.run import run_from_prd
    from heaven_base.baseheavenagent import HeavenAgentConfig
    from heaven_base.tool_utils.completion_runners import exec_completion_style
    from compoctopus.tools import CreatePRDTool, BuildPRDTool
    from compoctopus.octohead import make_octohead

    # Read the current codebase structure
    tree = run_cmd(f"find {WORKSPACE}/compoctopus -name '*.py' -type f | head -50")

    prompt = (
        f"My project is at {WORKSPACE}. Here is the file structure:\n\n"
        f"```\n{tree}\n```\n\n"
        f"{IMPROVEMENT_RULES}\n\n"
        "Review the codebase. Identify the single most impactful improvement. "
        "Create a PRD for it and queue it. Only ONE improvement per cycle."
    )

    config = make_octohead()
    result = await exec_completion_style(prompt=prompt, agent=config)

    # Extract response
    msgs = result.get("messages", [])
    if msgs:
        last = msgs[-1]
        content = last.get("content", "")
        if isinstance(content, list):
            text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
        else:
            text = str(content)
        logger.info("OctoHead response:\n%s", text[:500])

    return result


def wait_for_daemon_completion(timeout: int = 300) -> bool:
    """Wait for daemon to process all .🪸 files."""
    start = time.time()
    while time.time() - start < timeout:
        corals = list(Path(DAEMON_QUEUE).glob("*.🪸"))
        surfs = list(Path(DAEMON_QUEUE).glob("*.🏄"))
        if not corals and surfs:
            logger.info("Daemon completed: %d .🏄 reports", len(surfs))
            return True
        time.sleep(5)
    logger.warning("Daemon timeout after %ds", timeout)
    return False


def commit_and_pr():
    """Commit changes and open PR to develop."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch = f"auto-dev/{timestamp}"

    run_cmd(f"git checkout -b {branch}")
    run_cmd("git add -A")

    # Check if there are changes
    diff = run_cmd("git diff --cached --stat")
    if not diff:
        logger.info("No changes to commit")
        return False

    run_cmd(f'git commit -m "auto-dev: improvement cycle {timestamp}"')
    run_cmd(f"git push origin {branch}")

    # Open PR
    pr_url = run_cmd(
        f'gh pr create --base develop --head {branch} '
        f'--title "Auto-dev improvement {timestamp}" '
        f'--body "Automated improvement cycle by Compoctopus auto-dev loop."'
    )
    logger.info("PR created: %s", pr_url)
    return True


def clean_workspace():
    """Clean auto-dev workspace for next cycle."""
    # Clean daemon queue
    for f in Path(DAEMON_QUEUE).glob("*"):
        if f.is_file():
            f.unlink()
    done_dir = Path(DAEMON_QUEUE) / "done"
    if done_dir.exists():
        for f in done_dir.glob("*"):
            f.unlink()

    logger.info("Workspace cleaned")


async def single_cycle():
    """Run one auto-dev cycle."""
    logger.info("=" * 60)
    logger.info("🐙 Auto-dev cycle starting")
    logger.info("=" * 60)

    # 1. Pull latest
    pull_latest()

    # 2. OctoHead introspects and generates PRDs
    await run_octohead_autonomous()

    # 3. Wait for daemon to process
    # (daemon must be running separately)
    has_corals = list(Path(DAEMON_QUEUE).glob("*.🪸"))
    if has_corals:
        logger.info("Waiting for daemon to process %d corals...", len(has_corals))
        wait_for_daemon_completion()

    # 4. Commit and PR
    committed = commit_and_pr()

    # 5. Clean
    clean_workspace()

    if committed:
        logger.info("✅ Cycle complete — PR opened")
    else:
        logger.info("⏭️ Cycle complete — no changes")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compoctopus auto-dev loop")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between cycles (default: 1hr)")
    args = parser.parse_args()

    os.environ.setdefault("HEAVEN_DATA_DIR", "/tmp/heaven_data")

    if args.loop:
        while True:
            try:
                asyncio.run(single_cycle())
            except Exception as e:
                logger.error("Cycle failed: %s", e, exc_info=True)
            logger.info("Next cycle in %ds...", args.interval)
            time.sleep(args.interval)
    else:
        asyncio.run(single_cycle())


if __name__ == "__main__":
    main()
