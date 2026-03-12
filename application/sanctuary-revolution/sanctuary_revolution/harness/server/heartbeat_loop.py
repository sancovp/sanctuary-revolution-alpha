"""Heartbeat Loop — GNOSYS pulse.

Reads /tmp/heaven_data/heartbeat_config.json (Isaac-controlled).
Fires on interval, checks rituals + inbox, nags via Discord/logs.
V0: no auth, agent CAN edit config but SHOULDN'T.
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

HBC_PATH = Path("/tmp/heaven_data/heartbeat_config.json")
HBC_LOG_PATH = Path("/tmp/heaven_data/heartbeat_log.jsonl")
LOCK_PATH = Path("/tmp/heaven_data/heartbeat_user_active.lock")
LOCK_STALE_SECONDS = 300  # 5 minutes


def _read_config() -> dict:
    """Read heartbeat config. Returns empty dict if missing."""
    if HBC_PATH.exists():
        return json.loads(HBC_PATH.read_text())
    return {"enabled": False}


def _user_is_active() -> bool:
    """Check if human is actively using Claude Code.

    Returns True if lock file exists and is fresher than LOCK_STALE_SECONDS.
    """
    if not LOCK_PATH.exists():
        return False
    try:
        lock_data = json.loads(LOCK_PATH.read_text())
        ts = lock_data.get("ts", 0)
        return (time.time() - ts) < LOCK_STALE_SECONDS
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read lock file: {e}", exc_info=True)
        return False


def _log_beat(action: str, details: dict):
    """Append to heartbeat log."""
    entry = {"ts": datetime.utcnow().isoformat(), "action": action, **details}
    HBC_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HBC_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


async def _check_rituals(sanctum_builder) -> list:
    """Check ritual status, return list of overdue rituals."""
    try:
        sb = sanctum_builder()
        if not sb:
            return []
        status = sb.get_ritual_status() if hasattr(sb, 'get_ritual_status') else {}
        overdue = []
        now = datetime.now()
        for name, info in status.items() if isinstance(status, dict) else []:
            if not info.get("completed_today", False):
                overdue.append(name)
        return overdue
    except Exception as e:
        logger.error(f"Heartbeat ritual check failed: {e}", exc_info=True)
        return []


async def _check_inbox() -> int:
    """Check inbox count. Returns number of unread messages."""
    try:
        inbox_path = Path("/tmp/heaven_data/inbox")
        if inbox_path.exists():
            return len(list(inbox_path.glob("*.json")))
        return 0
    except Exception as e:
        logger.error(f"Heartbeat inbox check failed: {e}", exc_info=True)
        return 0


async def heartbeat_tick(get_sanctum_builder):
    """Single heartbeat tick — runs all on_wake checks."""
    config = _read_config()
    if not config.get("enabled", False):
        return

    if _user_is_active():
        _log_beat("skipped_user_active", {})
        return

    on_wake = config.get("on_wake", [])
    results = {}

    if "check_rituals" in on_wake:
        overdue = await _check_rituals(get_sanctum_builder)
        results["overdue_rituals"] = overdue
        if overdue:
            logger.info(f"HEARTBEAT NAG: {len(overdue)} rituals overdue: {overdue}")

    if "check_inbox" in on_wake:
        inbox_count = await _check_inbox()
        results["inbox_count"] = inbox_count

    _log_beat("tick", results)
    return results


async def heartbeat_loop(get_sanctum_builder):
    """Main heartbeat loop. Reads config each tick (hot-reloadable)."""
    logger.info("Heartbeat loop starting...")
    _log_beat("start", {"pid": "sancrev"})

    while True:
        try:
            config = _read_config()
            if not config.get("enabled", False):
                _log_beat("disabled", {})
                await asyncio.sleep(60)  # Check again in 60s if re-enabled
                continue

            interval = config.get("interval_seconds", 900)
            await heartbeat_tick(get_sanctum_builder)
            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            _log_beat("stopped", {})
            logger.info("Heartbeat loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            _log_beat("error", {"error": str(e)})
            await asyncio.sleep(60)
