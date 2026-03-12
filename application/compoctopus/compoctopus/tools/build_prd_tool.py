"""BuildPRDTool — moves a .🪸 PRD file to the Compoctopus daemon queue.

After CreatePRD writes and the user refines the .🪸 file,
BuildPRD moves it to the daemon queue where it gets picked up
and run through Planner → Bandit → OctoCoder.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from glob import glob
from pathlib import Path

logger = logging.getLogger(__name__)

DAEMON_QUEUE = "/tmp/compoctopus_daemon_queue"


def _ensure_daemon_running():
    """Start the Compoctopus daemon if it's not already running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python -m compoctopus.daemon"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            logger.info("Daemon already running (pid %s)", result.stdout.strip().split()[0])
            return

        # Not running — start it with proper env
        logger.info("Starting Compoctopus daemon...")
        cmd = (
            "source /home/GOD/system_config.sh 2>/dev/null; "
            "export HEAVEN_DATA_DIR=${HEAVEN_DATA_DIR:-/tmp/heaven_data}; "
            "source /workspace/venv/bin/activate 2>/dev/null; "
            f"cd /tmp/compoctopus && python -m compoctopus.daemon --queue {DAEMON_QUEUE} "
            ">> /tmp/daemon_run.log 2>&1"
        )
        subprocess.Popen(
            ["bash", "-c", cmd],
            start_new_session=True,
        )
        logger.info("Daemon started in background, log at /tmp/daemon_run.log")
    except Exception as e:
        logger.warning("Could not auto-start daemon: %s", e)


def build_prd(
    prd_path: str = "",
) -> str:
    """Send a .🪸 PRD to the Compoctopus daemon for building.

    Moves the most recent .🪸 file (or a specific one) to the daemon queue.
    The daemon watches this directory and runs the pipeline automatically.

    Args:
        prd_path: Path to a specific .🪸 PRD file. If empty, uses the most recent .🪸 in the working queue.

    Returns:
        Confirmation that the PRD has been sent to the daemon.
    """
    from compoctopus.prd import PRD

    # Find .🪸 file
    if not prd_path:
        working_dir = os.environ.get("COMPOCTOPUS_QUEUE", "/tmp/compoctopus_queue")
        corals = sorted(glob(f"{working_dir}/prd_*.🪸"))
        if not corals:
            return "ERROR: No .🪸 PRD files found. Call CreatePRD first."
        prd_path = corals[-1]  # most recent

    prd_path = Path(prd_path)
    if not prd_path.exists():
        return f"ERROR: File not found: {prd_path}"

    print(f"🔧 BuildPRD({prd_path.name})")

    # Validate the PRD
    try:
        with open(prd_path) as f:
            prd_dict = json.load(f)
        prd = PRD.from_dict(prd_dict)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        return f"ERROR: Invalid PRD at {prd_path}: {e}"

    # Move to daemon queue
    daemon_dir = Path(DAEMON_QUEUE)
    daemon_dir.mkdir(parents=True, exist_ok=True)
    dest = daemon_dir / prd_path.name
    shutil.move(str(prd_path), str(dest))

    logger.info("PRD '%s' sent to daemon: %s → %s", prd.name, prd_path, dest)

    # Auto-start daemon if not running
    _ensure_daemon_running()

    return (
        f"✅ PRD '{prd.name}' sent to daemon queue.\n"
        f"   From: {prd_path}\n"
        f"   To: {dest}\n"
        f"   Assertions: {len(prd.behavioral_assertions)}\n"
        f"   Daemon will run: Planner → Bandit → OctoCoder\n"
        f"   Results will appear as .🏄 file when complete."
    )


# Create the Heaven tool
try:
    from heaven_base.make_heaven_tool_from_docstring import make_heaven_tool_from_docstring
    BuildPRDTool = make_heaven_tool_from_docstring(build_prd, tool_name="BuildPRD")
except ImportError:
    BuildPRDTool = None
    logger.warning("heaven_base not available — BuildPRDTool disabled")
