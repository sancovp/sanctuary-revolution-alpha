#!/usr/bin/env python3
"""
Marks system for content pipeline.
Timestamps recording segments for ffmpeg post-processing.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .server import obs_client
from .server import mcp

# Marks file location
MARKS_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "content_marks"
MARKS_DIR.mkdir(parents=True, exist_ok=True)

# Current session marks file
_current_session: Optional[str] = None
_marks: List[Dict[str, Any]] = []


def _get_marks_file() -> Path:
    """Get current marks file path."""
    global _current_session
    if not _current_session:
        _current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
    return MARKS_DIR / f"marks_{_current_session}.json"


def _save_marks():
    """Save marks to file."""
    marks_file = _get_marks_file()
    marks_file.write_text(json.dumps({
        "session": _current_session,
        "marks": _marks
    }, indent=2))


@mcp.tool()
async def start_recording_session(name: Optional[str] = None) -> Dict[str, Any]:
    """
    Start a new recording session and begin OBS recording.
    Creates a new marks file for this session.

    Args:
        name: Optional session name (defaults to timestamp)

    Returns:
        Dict with session info
    """
    global _current_session, _marks

    _current_session = name or datetime.now().strftime("%Y%m%d_%H%M%S")
    _marks = []

    # Start OBS recording
    await obs_client.send_request("StartRecord")

    # Auto-add sync mark at t=0
    _marks.append({
        "t": 0.0,
        "label": "sync",
        "note": "Session start"
    })
    _save_marks()

    return {
        "session": _current_session,
        "marks_file": str(_get_marks_file()),
        "status": "recording"
    }


@mcp.tool()
async def mark(label: str, note: Optional[str] = None) -> Dict[str, Any]:
    """
    Mark current timestamp in the recording.

    Labels:
    - "good" = end of good take, keep this segment
    - "cut" = end of bad take, delete this segment
    - "redo" = delete back to last mark
    - "sync" = reference point (auto-added at start)
    - any custom label

    Args:
        label: Mark type (good, cut, redo, or custom)
        note: Optional note about this mark

    Returns:
        Dict with mark info including timestamp
    """
    global _marks

    # Get current recording time from OBS
    status = await obs_client.send_request("GetRecordStatus")

    if not status.get("outputActive"):
        return {"error": "Not currently recording"}

    # outputDuration is in milliseconds
    timestamp = status.get("outputDuration", 0) / 1000.0

    mark_entry = {
        "t": timestamp,
        "label": label,
    }
    if note:
        mark_entry["note"] = note

    _marks.append(mark_entry)
    _save_marks()

    return {
        "label": label,
        "t": timestamp,
        "total_marks": len(_marks)
    }


@mcp.tool()
async def stop_recording_session() -> Dict[str, Any]:
    """
    Stop the recording session.
    Returns video path and marks file path for post-processing.

    Returns:
        Dict with video_path, marks_file, and all marks
    """
    global _marks

    # Get final timestamp
    status = await obs_client.send_request("GetRecordStatus")
    final_t = status.get("outputDuration", 0) / 1000.0

    # Add end mark
    _marks.append({
        "t": final_t,
        "label": "end",
        "note": "Session end"
    })
    _save_marks()

    # Stop OBS recording
    result = await obs_client.send_request("StopRecord")
    video_path = result.get("outputPath", "")

    return {
        "video_path": video_path,
        "marks_file": str(_get_marks_file()),
        "marks": _marks,
        "total_duration": final_t
    }


@mcp.tool()
async def get_marks() -> Dict[str, Any]:
    """
    Get all marks from current session.

    Returns:
        Dict with session info and all marks
    """
    return {
        "session": _current_session,
        "marks_file": str(_get_marks_file()) if _current_session else None,
        "marks": _marks
    }


@mcp.tool()
async def undo_last_mark() -> Dict[str, Any]:
    """
    Remove the last mark (except sync mark).

    Returns:
        Dict with removed mark info
    """
    global _marks

    if len(_marks) <= 1:  # Keep at least the sync mark
        return {"error": "No marks to undo (sync mark preserved)"}

    removed = _marks.pop()
    _save_marks()

    return {
        "removed": removed,
        "remaining_marks": len(_marks)
    }
