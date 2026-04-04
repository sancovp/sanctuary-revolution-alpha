"""Observatory research queue runner.

The missing piece between the factory (make_researcher_compoctopus) and CAVE.
This module owns ALL queue logic. CAVE's ResearcherAgent DIs this as its runtime.

Queue entries have two types:
- START (status=pending): new investigation, runs full chain OBSERVE→EXPERIMENT, pauses
- RESUME (queue_type=resume): grug callback wrote data, runs ANALYZE with grug context
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .agents import make_researcher_compoctopus
from .config import PHASES

logger = logging.getLogger(__name__)

QUEUE_DIR = Path("/tmp/heaven_data/observatory")
QUEUE_FILE = QUEUE_DIR / "research_queue.json"


# =============================================================================
# Queue I/O
# =============================================================================

def load_queue() -> list:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text())
    return []


def save_queue(queue: list):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def write_resume(grug_result: dict) -> bool:
    """Write grug callback data into the queue on the matching investigation.

    Called by the HTTP endpoint when grug POSTs back with results.
    Returns True if the investigation was found and updated.
    """
    investigation_name = grug_result.get("investigation_name", "")
    if not investigation_name:
        logger.error("write_resume: no investigation_name in grug_result")
        return False

    queue = load_queue()
    for entry in queue:
        if entry["investigation_name"] == investigation_name:
            entry["grug_history_id"] = grug_result.get("history_id", "")
            entry["grug_history_path"] = grug_result.get("grug_history_path", "")
            entry["grug_status"] = grug_result.get("status", "")
            entry["queue_type"] = "resume"
            logger.info("Wrote RESUME data to queue for %s: path=%s",
                        investigation_name, entry["grug_history_path"])
            save_queue(queue)
            return True

    logger.error("write_resume: investigation %s not found in queue", investigation_name)
    return False


def recover_interrupted() -> int:
    """Find in_progress items and prepare them for resumption. Returns count."""
    queue = load_queue()
    changed = False

    for entry in queue:
        if entry.get("status") != "in_progress":
            continue
        if entry.get("last_completed_phase") is not None:
            # Items paused after EXPERIMENT are waiting for grug callback — don't auto-resume
            if "experiment" in entry.get("last_completed_phase_name", "").lower() and entry.get("queue_type") != "resume":
                logger.info("Awaiting grug callback (not resuming): %s", entry["investigation_name"])
                continue
            logger.info("Resumable: %s (completed through phase %d: %s)",
                        entry["investigation_name"],
                        entry["last_completed_phase"],
                        entry.get("last_completed_phase_name", "?"))
        else:
            entry["status"] = "pending"
            changed = True
            logger.info("Reset to pending (no progress): %s", entry["investigation_name"])

    if changed:
        save_queue(queue)

    return len([e for e in queue if e.get("status") == "in_progress"])


# =============================================================================
# Runner — the function that CAVE DIs as the runtime
# =============================================================================

_run_lock = asyncio.Lock()


async def run_research(on_notify: Optional[Callable] = None, on_message: Optional[Callable] = None) -> Dict[str, Any]:
    """Process next queue item. Only ONE research runs at a time.

    This is the function that CAVE's ResearcherAgent.run() calls.
    It owns all queue logic, chain building, and execution.

    Args:
        on_notify: Optional callback for phase/status notifications.
        on_message: Optional callback for SDNAC turn-by-turn output (EventBroadcaster).
    """
    if _run_lock.locked():
        logger.warning("run_research called but already running — rejecting")
        return {"status": "busy", "message": "Researcher is already running."}

    async with _run_lock:
        return await _run_research_locked(on_notify=on_notify, on_message=on_message)


async def _run_research_locked(on_notify: Optional[Callable] = None, on_message: Optional[Callable] = None) -> Dict[str, Any]:
    """Internal: process one queue item. Caller MUST hold _run_lock."""

    def notify(text: str):
        if on_notify:
            try:
                on_notify(text)
            except Exception as e:
                logger.error("Notify error: %s", e)

    queue = load_queue()

    # Priority 1: RESUME entries (grug called back)
    resume_entries = [e for e in queue if e.get("queue_type") == "resume" and e.get("status") == "in_progress"]
    # Priority 2: in_progress with phase progress (crash recovery) — NOT experiment-paused
    resumable = [e for e in queue if e.get("status") == "in_progress"
                 and e.get("last_completed_phase") is not None
                 and e.get("queue_type") != "resume"
                 and "experiment" not in e.get("last_completed_phase_name", "").lower()]
    # Priority 3: pending (new investigations)
    pending = [e for e in queue if e.get("status") == "pending"]

    if resume_entries:
        entry = resume_entries[0]
        is_resume = True
    elif resumable:
        entry = resumable[0]
        is_resume = True
    elif pending:
        entry = pending[0]
        is_resume = False
    else:
        return {"status": "empty", "message": "No research items to process"}

    entry["status"] = "in_progress"
    save_queue(queue)

    action = "Resuming" if is_resume else "Starting"
    notify(
        f"🔬 **Research {action.lower()}:** {entry['topic']}\n"
        f"Investigation: {entry['investigation_name']}\n"
        f"Pattern: CompoctopusAgent (Chain of SDNACs)"
    )

    # Build CompoctopusAgent
    compoctopus = make_researcher_compoctopus(
        topic=entry["topic"],
        domain=entry["domain"],
        investigation_name=entry["investigation_name"],
        hint=entry.get("hint", ""),
    )

    # Phase progress callback
    def _on_phase_complete(phase_index, phase_name):
        q = load_queue()
        for e in q:
            if e["investigation_name"] == entry["investigation_name"]:
                e["last_completed_phase"] = phase_index
                e["last_completed_phase_name"] = phase_name
        save_queue(q)
        logger.info("Research progress saved: phase %d (%s) complete", phase_index, phase_name)

    # Resume from last completed phase
    last_phase = entry.get("last_completed_phase")
    start_from = (last_phase if last_phase is not None else -1) + 1

    try:
        context = {
            "topic": entry["topic"],
            "domain": entry["domain"],
            "investigation_name": entry["investigation_name"],
            "hint": entry.get("hint", ""),
        }

        # Read grug data from queue entry (written by write_resume)
        if entry.get("grug_history_path"):
            context["grug_history_id"] = entry.get("grug_history_id", "")
            context["grug_history_path"] = entry["grug_history_path"]
            context["grug_status"] = entry.get("grug_status", "")

        if start_from > 0:
            notify(f"🔄 Resuming from phase {start_from} (skipping {start_from} completed phases)")

        result = await compoctopus.chain.execute(
            context, start_from=start_from,
            on_phase_complete=_on_phase_complete,
            on_message=on_message,
        )

        # Check for AWAITING_INPUT (chain paused after EXPERIMENT)
        is_awaiting = hasattr(result, 'status') and 'awaiting' in str(result.status).lower()
        if is_awaiting:
            notify(
                f"⏸️ **Research paused:** {entry['investigation_name']}\n"
                f"Waiting for grug to complete experiment. Will resume ANALYZE on callback."
            )
            return {
                "status": "awaiting_grug",
                "investigation": entry["investigation_name"],
                "last_phase": entry.get("last_completed_phase_name"),
            }

        # Check for errors
        is_error = False
        if hasattr(result, 'status'):
            is_error = str(result.status) not in ("success", "LinkStatus.SUCCESS")
        if hasattr(result, 'error') and result.error:
            is_error = True

        if is_error:
            error_msg = getattr(result, 'error', 'Unknown error')
            queue = load_queue()
            for e in queue:
                if e["investigation_name"] == entry["investigation_name"]:
                    e["status"] = "error"
                    e["error"] = str(error_msg)
            save_queue(queue)
            notify(f"❌ **Research FAILED:** {entry['investigation_name']}\nError: {error_msg}")
            return {"status": "error", "investigation": entry["investigation_name"], "error": str(error_msg)}

        # Success
        completed_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        queue = load_queue()
        for e in queue:
            if e["investigation_name"] == entry["investigation_name"]:
                e["status"] = "completed"
                e["completed_at"] = completed_at
                e.pop("queue_type", None)
        save_queue(queue)
        notify(f"✅ **Research completed:** {entry['investigation_name']}")
        return {"status": "completed", "investigation": entry["investigation_name"], "topic": entry["topic"]}

    except Exception as e:
        logger.error("Research failed: %s — %s", entry["investigation_name"], e, exc_info=True)
        queue = load_queue()
        for qe in queue:
            if qe["investigation_name"] == entry["investigation_name"]:
                qe["status"] = "error"
                qe["error"] = str(e)
        save_queue(queue)
        notify(f"❌ **Research failed:** {entry['investigation_name']}\nError: {e}")
        return {"status": "error", "investigation": entry["investigation_name"], "error": str(e)}


def get_status() -> Dict[str, Any]:
    """Current queue status."""
    queue = load_queue()
    return {
        "queue_pending": len([e for e in queue if e.get("status") == "pending"]),
        "queue_in_progress": len([e for e in queue if e.get("status") == "in_progress"]),
        "queue_resume": len([e for e in queue if e.get("queue_type") == "resume"]),
        "queue_total": len(queue),
    }
