#!/usr/bin/env python3
"""
Flight Status Hook - Inject course state and waypoint progress on user messages

Injects status on:
- First message of conversation
- Every 5 messages thereafter
"""

import json
import os
import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Counter file to track message count
COUNTER_FILE = "/tmp/heaven_data/omnisanc_core/.message_counter"
COURSE_STATE_FILE = "/tmp/heaven_data/omnisanc_core/.course_state"

def get_message_count() -> int:
    """Get current message count"""
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return 0

def increment_message_count() -> int:
    """Increment and return new message count"""
    count = get_message_count() + 1
    os.makedirs(os.path.dirname(COUNTER_FILE), exist_ok=True)
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(count))
    return count

def get_course_state() -> dict:
    """Read course state"""
    try:
        if os.path.exists(COURSE_STATE_FILE):
            with open(COURSE_STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_waypoint_state(project_path: str) -> dict:
    """Read waypoint state for a project"""
    try:
        project_name = os.path.basename(project_path.rstrip('/'))
        waypoint_file = f"/tmp/waypoint_state_{project_name}.json"
        if os.path.exists(waypoint_file):
            with open(waypoint_file, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def format_course_info(course: dict) -> list:
    """Format course-related status lines"""
    lines = []
    mode = "JOURNEY MODE" if course.get("course_plotted") else "HOME MODE"
    lines.append(f"📍 Status: {mode}")

    if course.get("projects"):
        project = course["projects"][0] if course["projects"] else "unknown"
        lines.append(f"   Project: {project}")

    if course.get("domain"):
        domain_str = course["domain"]
        if course.get("subdomain"):
            domain_str += f"/{course['subdomain']}"
        if course.get("process"):
            domain_str += f"/{course['process']}"
        lines.append(f"   Domain: {domain_str}")
    return lines

def format_waypoint_info(course: dict) -> list:
    """Format waypoint-related status lines"""
    lines = []
    if course.get("projects"):
        waypoint = get_waypoint_state(course["projects"][0])
        if waypoint.get("status") == "IN_PROGRESS":
            config_name = waypoint.get("config_filename", "unknown")
            current = waypoint.get("last_served_sequence", 0)
            total = waypoint.get("total_waypoints", 0)
            lines.append(f"   Flight: {config_name} (step {current}/{total})")
    return lines

def format_mission_info(course: dict) -> list:
    """Format mission-related status lines"""
    lines = []
    if course.get("mission_active"):
        mission_id = course.get("mission_id", "unknown")
        mission_step = course.get("mission_step", 0)
        lines.append(f"   Mission: {mission_id} (step {mission_step})")
    return lines

def format_status() -> str:
    """Format current flight status"""
    course = get_course_state()

    if not course.get("course_plotted"):
        return "📍 Status: HOME MODE (no active course)"

    lines = format_course_info(course)
    lines.extend(format_waypoint_info(course))
    lines.extend(format_mission_info(course))

    return "\n".join(lines)

def should_inject(count: int) -> bool:
    """Determine if we should inject status"""
    # First message or every 5 messages
    return count == 1 or count % 5 == 0

def main():
    try:
        hook_data = json.load(sys.stdin)

        # Increment counter
        count = increment_message_count()

        # Check if we should inject
        if not should_inject(count):
            print(json.dumps(hook_data))
            sys.exit(0)

        # Get status
        status = format_status()

        # Inject using correct hook format
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": status
            }
        }

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # On error, pass through unchanged
        logger.error(f"Flight status hook error: {e}", exc_info=True)
        print(json.dumps({}))
        sys.exit(0)

if __name__ == "__main__":
    main()
