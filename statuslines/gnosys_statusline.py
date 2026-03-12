#!/usr/bin/env python3
"""
GNOSYS Status Line - Combined OMNISANC/STARSYSTEM state + context monitor
"""

import json
import sys
import os
import re
import logging
import traceback

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

COURSE_STATE_FILE = os.environ.get(
    "COURSE_STATE_FILE",
    "/tmp/heaven_data/omnisanc_core/.course_state"
)
OMNISANC_DISABLED_FILE = "/tmp/heaven_data/omnisanc_core/.omnisanc_disabled"
BRAINHOOK_STATE_FILE = "/tmp/brainhook_state.txt"
AUTOPOIESIS_PROMISE_FILE = "/tmp/active_promise.md"
BE_MYSELF_TOGGLE_FILE = "/tmp/heaven_data/giint/be_myself_enabled"
CARTON_QUEUE_DIR = "/tmp/heaven_data/carton_queue"
INNER_TEACHER_PID_FILE = "/tmp/inner_teacher_data/inner_teacher.pid"


# =============================================================================
# CONTEXT MONITOR
# =============================================================================

def _parse_usage_tokens(data: dict) -> dict | None:
    """Parse token usage from assistant message."""
    usage = data.get('message', {}).get('usage', {})
    if not usage:
        return None
    input_tokens = usage.get('input_tokens', 0)
    cache_read = usage.get('cache_read_input_tokens', 0)
    cache_creation = usage.get('cache_creation_input_tokens', 0)
    total = input_tokens + cache_read + cache_creation
    if total > 0:
        # Add 14% adjustment (Anthropic changed context reporting Jan 2026)
        raw_percent = (total / 200000) * 100
        adjusted_percent = min(100, raw_percent + 14)
        return {'percent': adjusted_percent, 'tokens': total}
    return None


def _parse_system_warning(content: str) -> dict | None:
    """Parse context warning from system message."""
    match = re.search(r'Context left until auto-compact: (\d+)%', content)
    if match:
        return {'percent': 100 - int(match.group(1)), 'warning': 'auto-compact'}
    match = re.search(r'Context low \((\d+)% remaining\)', content)
    if match:
        return {'percent': 100 - int(match.group(1)), 'warning': 'low'}
    return None


def parse_context_from_transcript(transcript_path: str) -> dict | None:
    """Parse context usage from transcript file."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    try:
        with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()[-15:]
        for line in reversed(lines):
            try:
                data = json.loads(line.strip())
                if data.get('type') == 'assistant':
                    result = _parse_usage_tokens(data)
                    if result:
                        return result
                elif data.get('type') == 'system_message':
                    result = _parse_system_warning(data.get('content', ''))
                    if result:
                        return result
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    except Exception as e:
        logger.debug(f"Failed to parse transcript: {e}\n{traceback.format_exc()}")
    return None


def _get_context_color(percent: float) -> str:
    """Get ANSI color for context percentage."""
    if percent >= 95:
        return "\033[31;1m"
    elif percent >= 90:
        return "\033[31m"
    elif percent >= 75:
        return "\033[91m"
    elif percent >= 50:
        return "\033[33m"
    return "\033[32m"


CONTEXT_PERCENT_FILE = "/tmp/context_percent.txt"


def _write_context_to_file(percent: float) -> None:
    """Write context percentage to file for hook consumption."""
    try:
        with open(CONTEXT_PERCENT_FILE, 'w') as f:
            f.write(f"{percent:.0f}")
    except Exception as e:
        logger.debug(f"Failed to write context percent: {e}\n{traceback.format_exc()}")


def format_context(context_info: dict | None) -> str:
    """Format context bar with percentage."""
    if not context_info:
        return "???"
    percent = context_info.get('percent', 0)
    # Write to file for PostToolUse hook
    _write_context_to_file(percent)
    filled = int((percent / 100) * 8)
    bar = "█" * filled + "▁" * (8 - filled)
    color = _get_context_color(percent)
    alert = " AUTO!" if context_info.get('warning') == 'auto-compact' else ""
    alert = " LOW!" if context_info.get('warning') == 'low' else alert
    return f"{color}{bar}\033[0m {percent:.0f}%{alert}"


def _format_cost(cost_usd: float) -> str | None:
    """Format cost metric."""
    if cost_usd <= 0:
        return None
    color = "\033[31m" if cost_usd >= 0.10 else "\033[33m" if cost_usd >= 0.05 else "\033[32m"
    cost_str = f"{cost_usd*100:.0f}¢" if cost_usd < 0.01 else f"${cost_usd:.2f}"
    return f"{color}💰{cost_str}\033[0m"


def _format_duration(duration_ms: int) -> str | None:
    """Format duration metric."""
    if duration_ms <= 0:
        return None
    minutes = duration_ms / 60000
    color = "\033[33m" if minutes >= 30 else "\033[32m"
    duration_str = f"{duration_ms//1000}s" if minutes < 1 else f"{minutes:.0f}m"
    return f"{color}⏱{duration_str}\033[0m"


def _format_lines(added: int, removed: int) -> str | None:
    """Format lines changed metric."""
    if added <= 0 and removed <= 0:
        return None
    net = added - removed
    color = "\033[32m" if net > 0 else "\033[31m" if net < 0 else "\033[33m"
    sign = "+" if net >= 0 else ""
    return f"{color}📝{sign}{net}\033[0m"


def format_session_metrics(cost_data: dict) -> str | None:
    """Format cost/time/lines metrics."""
    if not cost_data:
        return None
    parts = [
        _format_cost(cost_data.get('total_cost_usd', 0)),
        _format_duration(cost_data.get('total_duration_ms', 0)),
        _format_lines(cost_data.get('total_lines_added', 0), cost_data.get('total_lines_removed', 0))
    ]
    parts = [p for p in parts if p]
    return " ".join(parts) if parts else None


def format_model(model_data: dict) -> str | None:
    """Format model name."""
    name = model_data.get('display_name', '')
    return f"\033[94m[{name}]\033[0m" if name else None


# =============================================================================
# GNOSYS STATE
# =============================================================================

def get_course_state() -> dict:
    """Read course state."""
    try:
        if os.path.exists(COURSE_STATE_FILE):
            with open(COURSE_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to read course state: {e}\n{traceback.format_exc()}")
    return {}


def get_waypoint_state(project_path: str) -> dict:
    """Read waypoint state for a project."""
    try:
        project_name = os.path.basename(project_path.rstrip('/'))
        waypoint_file = f"/tmp/waypoint_state_{project_name}.json"
        if os.path.exists(waypoint_file):
            with open(waypoint_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to read waypoint state: {e}\n{traceback.format_exc()}")
    return {}


def format_mode(course: dict) -> str:
    return "🚀 JRN" if course.get("course_plotted") else "🏠 HOME"


def format_project(course: dict) -> str | None:
    if course.get("projects"):
        return f"📁 {os.path.basename(course['projects'][0].rstrip('/'))}"
    return None


def format_domain(course: dict) -> str | None:
    if not course.get("domain"):
        return None
    domain_str = course["domain"]
    if course.get("subdomain"):
        domain_str += f"/{course['subdomain']}"
    return f"🌐 {domain_str}"


def format_mission(course: dict) -> str | None:
    if not course.get("mission_active"):
        return None
    mission_id = course.get("mission_id", "?")
    step = course.get("mission_step", 0)
    short_id = "base" if mission_id.startswith("base_mission") else mission_id[:15]
    return f"🎯 {short_id}:{step}"


def format_waypoint(course: dict) -> str | None:
    if not course.get("projects"):
        return None
    waypoint = get_waypoint_state(course["projects"][0])
    if not waypoint:
        return None
    status = waypoint.get("status", "")
    config = waypoint.get("config_filename", "flight").replace("_flight_config", "").replace(".json", "")[:12]
    if status == "IN_PROGRESS":
        return f"✈️ {config}:{waypoint.get('last_served_sequence', 0)}/{waypoint.get('total_waypoints', 0)}"
    elif status == "END":
        return f"✈️ {config}:✓"
    return None


def is_omnisanc_enabled() -> bool:
    """Check if OMNISANC is enabled (disabled file doesn't exist)."""
    return not os.path.exists(OMNISANC_DISABLED_FILE)


def is_brainhook_enabled() -> bool:
    """Check if brainhook is enabled."""
    try:
        if os.path.exists(BRAINHOOK_STATE_FILE):
            with open(BRAINHOOK_STATE_FILE, 'r') as f:
                return f.read().strip().lower() == "on"
    except Exception:
        pass
    return False


def is_promise_active() -> bool:
    """Check if autopoiesis promise is active."""
    return os.path.exists(AUTOPOIESIS_PROMISE_FILE)


def is_be_myself_enforced() -> bool:
    """Check if be_myself enforcement is ON (default) or OFF."""
    try:
        if os.path.exists(BE_MYSELF_TOGGLE_FILE):
            with open(BE_MYSELF_TOGGLE_FILE, 'r') as f:
                return f.read().strip().upper() != "OFF"
    except Exception:
        pass
    return True  # Default: enforcement ON


def format_shield(course: dict) -> str | None:
    """Format OMNISANC status - green if enabled, red if disabled."""
    return "🛡️🟢" if is_omnisanc_enabled() else "🛡️🔴"


def format_brainhook() -> str:
    """Format brainhook status - green if on, red if off."""
    return "🧠🟢" if is_brainhook_enabled() else "🧠🔴"


def format_promise() -> str:
    """Format autopoiesis promise status - green if active, red if not."""
    return "🤝🟢" if is_promise_active() else "🤝🔴"


def format_be_myself() -> str:
    """Format be_myself enforcement - 😇 if enforced, 😈 if off."""
    return "😇" if is_be_myself_enforced() else "😈"


def get_carton_daemon_status() -> tuple[bool, int]:
    """Check if carton daemon is running and queue size."""
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", "observation_worker"],
            capture_output=True, timeout=1
        )
        is_running = result.returncode == 0
    except Exception:
        is_running = False

    queue_size = 0
    try:
        if os.path.exists(CARTON_QUEUE_DIR):
            queue_size = len([f for f in os.listdir(CARTON_QUEUE_DIR) if f.endswith('.json')])
    except Exception:
        pass

    return is_running, queue_size


def format_carton() -> str:
    """Format carton daemon status - 📦🟢 if running, 📦🔴 if dead, with queue count."""
    is_running, queue_size = get_carton_daemon_status()
    status = "🟢" if is_running else "🔴"
    if queue_size > 1000:
        return f"📦{status}{queue_size//1000}k"
    elif queue_size > 0:
        return f"📦{status}{queue_size}"
    return f"📦{status}"


def is_inner_teacher_running() -> bool:
    """Check if Inner Teacher daemon is running."""
    try:
        if os.path.exists(INNER_TEACHER_PID_FILE):
            with open(INNER_TEACHER_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
    except (OSError, ValueError):
        pass
    return False


def format_inner_teacher() -> str:
    """Format Inner Teacher status - 🎓🟢 if running, 🎓🔴 if not."""
    return "🎓🟢" if is_inner_teacher_running() else "🎓🔴"


def format_flags(course: dict) -> list[str]:
    flags = []
    if course.get("needs_review"):
        flags.append("⚠️REV")
    if course.get("landing_routine_called"):
        flags.append("🛬")
    return flags


def format_gnosys_state(course: dict) -> str:
    """Format GNOSYS state as compact emoji K:V pairs."""
    segments = [format_mode(course)]
    for fmt in [format_project, format_domain, format_mission, format_waypoint, format_shield]:
        result = fmt(course)
        if result:
            segments.append(result)
    # Add brainhook, promise, be_myself, carton, and inner teacher status
    segments.append(format_brainhook())
    segments.append(format_promise())
    segments.append(format_be_myself())
    segments.append(format_carton())
    segments.append(format_inner_teacher())
    segments.extend(format_flags(course))
    return " | ".join(segments)


# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        data = json.load(sys.stdin)
        parts = []

        # Context bar (with 24% overhead fix)
        context_info = parse_context_from_transcript(data.get('transcript_path', ''))
        parts.append(format_context(context_info))

        # GNOSYS state
        course = get_course_state()
        parts.append(format_gnosys_state(course))

        print(" | ".join(parts))

    except Exception as e:
        logger.error(f"Status line error: {e}\n{traceback.format_exc()}")
        print(f"🧠 ??? | 🏠 HOME | ❌ {str(e)[:15]}")


if __name__ == "__main__":
    main()
