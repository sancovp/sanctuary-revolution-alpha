"""
Sophia-MCP: Thin interface to Sophia daemon

Queues jobs for background processing, checks results, manages notifications.
The actual DUOAgent execution happens in the daemon.

Daemon auto-starts when MCP loads.
"""

import json
import uuid
import os
import subprocess
import sys
from typing import Optional, Literal
from pathlib import Path
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sophia-mcp")

# =============================================================================
# AUTO-START DAEMON
# =============================================================================

DAEMON_PID_FILE = Path("/tmp/sophia_daemon.pid")

def is_daemon_running() -> bool:
    """Check if daemon is running."""
    if not DAEMON_PID_FILE.exists():
        return False
    try:
        pid = int(DAEMON_PID_FILE.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        return True
    except (ProcessLookupError, ValueError):
        DAEMON_PID_FILE.unlink(missing_ok=True)
        return False

def start_daemon():
    """Start the daemon if not running."""
    if is_daemon_running():
        return

    # Start daemon as subprocess
    proc = subprocess.Popen(
        [sys.executable, "-m", "sophia_mcp.daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    DAEMON_PID_FILE.write_text(str(proc.pid))

# Auto-start on import
start_daemon()

# Paths (same as daemon)
SOPHIA_DATA_DIR = Path(os.environ.get("SOPHIA_DATA_DIR", "/tmp/sophia_data"))
QUEUE_DIR = SOPHIA_DATA_DIR / "queue"
RESULTS_DIR = SOPHIA_DATA_DIR / "results"
FORKS_DIR = SOPHIA_DATA_DIR / "forks"
QUARANTINE_DIR = SOPHIA_DATA_DIR / "quarantine"
GOLDEN_DIR = SOPHIA_DATA_DIR / "golden"
NOTIFICATIONS_FILE = SOPHIA_DATA_DIR / "notifications.json"

for d in [QUEUE_DIR, RESULTS_DIR, FORKS_DIR, QUARANTINE_DIR, GOLDEN_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# =============================================================================
# JOB QUEUE HELPERS
# =============================================================================

def queue_job(job_type: str, **kwargs) -> str:
    """Queue a job for the daemon. Returns job_id."""
    job_id = f"{job_type}_{uuid.uuid4().hex[:8]}"
    job_data = {
        "job_id": job_id,
        "job_type": job_type,
        "queued_at": datetime.now().isoformat(),
        **kwargs
    }
    job_file = QUEUE_DIR / f"{job_id}.json"
    job_file.write_text(json.dumps(job_data, indent=2))
    return job_id


def get_result(job_id: str) -> Optional[dict]:
    """Get result for a job if completed."""
    result_file = RESULTS_DIR / f"{job_id}.json"
    if result_file.exists():
        return json.loads(result_file.read_text())
    return None


def is_queued(job_id: str) -> bool:
    """Check if job is still in queue."""
    return (QUEUE_DIR / f"{job_id}.json").exists()


# =============================================================================
# MCP TOOLS
# =============================================================================

@mcp.tool()
async def ask_sophia(context: str) -> dict:
    """
    Get wisdom/routing analysis from Sophia.

    Returns complexity level (L0-L6), routing decision, and resume_id
    for potential construct() call.

    Args:
        context: Description of what you're trying to accomplish

    Returns:
        dict with: analysis, complexity_level, complexity_description,
                   routing, resume_id
    """
    job_id = queue_job("ask", context=context)
    return {
        "status": "queued",
        "job_id": job_id,
        "message": "Job queued for Sophia daemon. Use check_job() to get result.",
    }


@mcp.tool()
async def construct(
    prompt: str,
    resume_id: Optional[str] = None,
    mode: Optional[str] = None,
) -> dict:
    """
    Build mode. Creates new chain (quarantined until goldenized).

    Can resume from ask_sophia context via resume_id.

    Args:
        prompt: What to construct/design
        resume_id: Optional job_id from ask_sophia to continue context
        mode: Build mode — "single" | "flow" | "duo". Auto-detected if None.

    Returns:
        dict with job_id for polling via check_job()
    """
    prior_context = ""
    history_id = None
    if resume_id:
        result = get_result(resume_id)
        if result:
            prior_context = f"Previous plan: {result.get('analysis', '')}"
            history_id = result.get("history_id")
        else:
            fork_file = FORKS_DIR / f"{resume_id}.json"
            if fork_file.exists():
                fork_data = json.loads(fork_file.read_text())
                prior_context = f"Previous: {fork_data.get('analysis', '')}"

    job_id = queue_job(
        "construct", prompt=prompt, prior_context=prior_context,
        resume_id=resume_id, mode=mode, history_id=history_id,
    )
    return {
        "status": "queued",
        "job_id": job_id,
        "message": "Job queued for Sophia daemon. Use check_job() to get result.",
    }


@mcp.tool()
async def check_job(job_id: str) -> dict:
    """
    Check status of a Sophia job.

    Args:
        job_id: The job ID returned from ask_sophia or construct

    Returns:
        dict with status and result if completed
    """
    # Check if still queued
    if is_queued(job_id):
        return {"status": "queued", "job_id": job_id}

    # Check for result
    result = get_result(job_id)
    if result:
        return result

    return {"status": "not_found", "job_id": job_id}


@mcp.tool()
async def list_jobs() -> dict:
    """
    List all Sophia jobs (queued and completed).

    Returns:
        dict with queued and completed job lists
    """
    queued = [f.stem for f in QUEUE_DIR.glob("*.json")]
    completed = [f.stem for f in RESULTS_DIR.glob("*.json")]

    return {
        "queued": queued,
        "queued_count": len(queued),
        "completed": completed[-10:],  # Last 10
        "completed_count": len(completed),
    }


@mcp.tool()
async def get_notifications(mark_read: bool = False) -> dict:
    """
    Get Sophia notifications (job completions).

    Args:
        mark_read: If True, mark all notifications as read

    Returns:
        dict with notifications list
    """
    if not NOTIFICATIONS_FILE.exists():
        return {"notifications": [], "unread_count": 0}

    notis = json.loads(NOTIFICATIONS_FILE.read_text())
    unread = [n for n in notis if not n.get("read")]

    if mark_read and unread:
        for n in notis:
            n["read"] = True
        NOTIFICATIONS_FILE.write_text(json.dumps(notis, indent=2))

    return {
        "notifications": notis[-10:],  # Last 10
        "unread_count": len(unread),
    }


@mcp.tool()
async def golden_management(
    operation: Literal["add", "delete", "list", "search"],
    query_or_name: Optional[str] = None
) -> dict:
    """
    Human-controlled goldenization. Agent proposes, human approves.

    Operations:
    - add: Promote quarantined chain to golden (requires chain_id)
    - delete: Remove golden chain (requires chain name)
    - list: Show all golden chains
    - search: RAG search over golden chains (requires query)

    Args:
        operation: One of "add", "delete", "list", "search"
        query_or_name: Chain ID/name for add/delete, search query for search

    Returns:
        dict with operation results
    """
    if operation == "list":
        golden_chains = []
        for chain_file in GOLDEN_DIR.glob("*.json"):
            data = json.loads(chain_file.read_text())
            golden_chains.append({
                "name": data.get("name", chain_file.stem),
                "prompt": data.get("prompt", "")[:100],
                "created_at": data.get("goldenized_at"),
            })
        return {"operation": "list", "count": len(golden_chains), "chains": golden_chains}

    elif operation == "add":
        if not query_or_name:
            return {"error": "chain_id required"}

        quarantine_file = QUARANTINE_DIR / f"{query_or_name}.json"
        if not quarantine_file.exists():
            return {"error": f"Not found: {query_or_name}"}

        data = json.loads(quarantine_file.read_text())
        data["goldenized_at"] = datetime.now().isoformat()
        data["name"] = query_or_name

        golden_file = GOLDEN_DIR / f"{query_or_name}.json"
        golden_file.write_text(json.dumps(data, indent=2))
        quarantine_file.unlink()

        return {"operation": "add", "success": True, "name": query_or_name}

    elif operation == "delete":
        if not query_or_name:
            return {"error": "name required"}
        golden_file = GOLDEN_DIR / f"{query_or_name}.json"
        if golden_file.exists():
            golden_file.unlink()
            return {"operation": "delete", "success": True}
        return {"error": f"Not found: {query_or_name}"}

    elif operation == "search":
        if not query_or_name:
            return {"error": "query required"}
        matches = []
        for chain_file in GOLDEN_DIR.glob("*.json"):
            data = json.loads(chain_file.read_text())
            if query_or_name.lower() in json.dumps(data).lower():
                matches.append({"name": chain_file.stem, "prompt": data.get("prompt", "")[:100]})
        return {"operation": "search", "query": query_or_name, "matches": matches}

    return {"error": f"Unknown operation: {operation}"}


if __name__ == "__main__":
    mcp.run()
