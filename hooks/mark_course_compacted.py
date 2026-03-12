#!/usr/bin/env python3
"""
OMNISANC Core - Mark Course Compacted Hook

This hook fires when conversation is about to be compacted.
It marks the current course state as compacted so that on continuation,
the user must explicitly continue_course() or plot_course().
"""

import os
import sys
import json
import logging

# Get logger
logger = logging.getLogger(__name__)

# Course state file
COURSE_STATE_FILE = "/tmp/heaven_data/omnisanc_core/.course_state"

def mark_course_compacted():
    """Mark the current course as compacted if one exists."""
    try:
        if not os.path.exists(COURSE_STATE_FILE):
            # No active course, nothing to mark
            logger.info("No active course to mark as compacted")
            return

        # Read current state
        with open(COURSE_STATE_FILE, 'r') as f:
            course_state = json.load(f)

        if not course_state.get("course_plotted", False):
            # No active course
            logger.info("No active course to mark as compacted")
            return

        # Mark as compacted
        course_state["was_compacted"] = True
        course_state["oriented"] = False  # Must re-orient after compact

        # Save updated state
        with open(COURSE_STATE_FILE, 'w') as f:
            json.dump(course_state, f, indent=2)

        project_path = course_state.get("project_path", "unknown")
        logger.info(f"Marked course as compacted: {project_path}")

    except Exception as e:
        logger.error(f"Failed to mark course as compacted: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        # Mark course as compacted
        mark_course_compacted()

        # Always allow compact to proceed
        sys.exit(0)

    except Exception as e:
        # Log error but don't block compact
        logger.error(f"Error in mark_course_compacted hook: {e}", exc_info=True)
        sys.exit(0)
