"""
Waitlist utils for Claude Code native conversation ingestion.

Provides interface to:
1. Read current transcript info (written by hook)
2. Manage ingestion waitlist (flag, list, remove conversations)

Storage:
- Current transcript: $HEAVEN_DATA_DIR/current_transcript.json (written by hook)
- Waitlist: $HEAVEN_DATA_DIR/ingestion_waitlist.json (persistent)
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# PATHS
# =============================================================================

def get_heaven_data_dir() -> str:
    """Get HEAVEN_DATA_DIR from env, with fallback."""
    return os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def get_waitlist_file() -> str:
    """Path to ingestion waitlist."""
    return os.path.join(get_heaven_data_dir(), "ingestion_waitlist.json")


def get_claude_home() -> Optional[str]:
    """Get CLAUDE_HOME from env."""
    return os.environ.get("CLAUDE_HOME")


# =============================================================================
# MODELS
# =============================================================================

class WaitlistEntry(BaseModel):
    """A conversation flagged for ingestion."""
    conversation_id: str
    flagged_at: str  # ISO timestamp
    reason: str
    priority: int = Field(default=5, ge=1, le=10)  # 1-10, higher = more important
    source: str = "claude_code"  # "claude_code", "openai", etc.
    transcript_path: Optional[str] = None
    status: Literal["pending", "in_progress", "ingested", "skipped"] = "pending"


# =============================================================================
# CLAUDE TRANSCRIPT DISCOVERY (filesystem-based)
# =============================================================================

def _cwd_to_project_folder(cwd: str) -> str:
    """Convert CWD to Claude project folder name. /home/GOD -> -home-GOD"""
    return cwd.replace("/", "-")


def _get_projects_dir(cwd: str, claude_home: str) -> Optional[Path]:
    """Get projects directory for a CWD."""
    project_folder = _cwd_to_project_folder(cwd)
    projects_dir = Path(claude_home) / "projects" / project_folder
    if not projects_dir.is_dir():
        logger.warning("Projects dir not found: %s", projects_dir)
        return None
    return projects_dir


def _find_latest_in_dir(projects_dir: Path) -> Optional[Path]:
    """Find most recent .jsonl file by mtime, excluding agent- files."""
    latest: Optional[Path] = None
    latest_mtime: float = -1.0
    for f in projects_dir.glob("*.jsonl"):
        if f.name.startswith("agent-"):
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            logger.debug("Could not stat %s", f, exc_info=True)
            continue
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest = f
    return latest


def get_latest_transcript(cwd: str, claude_home: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Find most recent transcript for a project.

    Args:
        cwd: The working directory (e.g., /home/GOD)
        claude_home: Path to .claude directory (default: from CLAUDE_HOME env)

    Returns:
        (transcript_path, session_id) or (None, None)
    """
    if claude_home is None:
        claude_home = get_claude_home()
    if not claude_home:
        logger.warning("CLAUDE_HOME not set and no claude_home provided")
        return None, None

    projects_dir = _get_projects_dir(cwd, claude_home)
    if not projects_dir:
        return None, None

    latest = _find_latest_in_dir(projects_dir)
    if latest is None:
        return None, None

    return str(latest), latest.stem


def get_current_session_id(cwd: str, claude_home: Optional[str] = None) -> Optional[str]:
    """Get most recent session ID for a project."""
    _, session_id = get_latest_transcript(cwd, claude_home)
    return session_id


def get_current_transcript_path(cwd: str, claude_home: Optional[str] = None) -> Optional[str]:
    """Get most recent transcript path for a project."""
    transcript_path, _ = get_latest_transcript(cwd, claude_home)
    return transcript_path


# =============================================================================
# WAITLIST STORAGE
# =============================================================================

def load_waitlist() -> Dict[str, WaitlistEntry]:
    """Load waitlist from disk. Returns dict keyed by conversation_id."""
    filepath = get_waitlist_file()
    if not os.path.exists(filepath):
        return {}

    with open(filepath, 'r') as f:
        data = json.load(f)

    return {k: WaitlistEntry.model_validate(v) for k, v in data.items()}


def save_waitlist(waitlist: Dict[str, WaitlistEntry]):
    """Save waitlist to disk."""
    filepath = get_waitlist_file()
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w') as f:
        json.dump({k: v.model_dump() for k, v in waitlist.items()}, f, indent=2)


# =============================================================================
# WAITLIST OPERATIONS
# =============================================================================

def flag_for_ingestion(
    conversation_id: str,
    reason: str,
    priority: int = 5,
    source: str = "claude_code",
    transcript_path: Optional[str] = None
) -> str:
    """
    Flag a conversation for later ingestion.

    Returns success message or error.
    """
    waitlist = load_waitlist()

    if conversation_id in waitlist:
        existing = waitlist[conversation_id]
        if existing.status == "pending":
            return f"Already flagged: {conversation_id} (priority {existing.priority}, reason: {existing.reason})"

    entry = WaitlistEntry(
        conversation_id=conversation_id,
        flagged_at=datetime.now().isoformat(),
        reason=reason,
        priority=priority,
        source=source,
        transcript_path=transcript_path,
        status="pending"
    )

    waitlist[conversation_id] = entry
    save_waitlist(waitlist)

    return f"✓ Flagged for ingestion: {conversation_id} (priority {priority})"


def _get_transcript_guide(cwd: str) -> str:
    """Return guide docs for finding/reading transcripts."""
    claude_home = get_claude_home() or "$CLAUDE_HOME"
    project_folder = _cwd_to_project_folder(cwd)
    return f"""=== Claude Code Transcript Guide ===

Transcripts location:
  {claude_home}/projects/{project_folder}/*.jsonl

To browse transcripts:
  1. Use Glob to list: {claude_home}/projects/{project_folder}/*.jsonl
  2. Use Read to view a transcript
  3. Session ID = filename without .jsonl extension
  4. Most recent = highest mtime

To flag a specific conversation:
  flag_conversation(cwd="{cwd}", reason="...", current=False, conversation_id="<session_id>")

To flag current conversation:
  flag_conversation(cwd="{cwd}", reason="...")
"""


def flag_conversation(
    cwd: str,
    reason: str = "",
    priority: int = 5,
    current: bool = True,
    conversation_id: Optional[str] = None,
    transcript_path: Optional[str] = None,
    guide: bool = False
) -> str:
    """
    Flag a conversation for later ingestion.

    Args:
        cwd: The working directory (Claude knows this)
        reason: Why this conversation should be ingested
        priority: 1-10, higher = more important (default: 5)
        current: If True, flag the most recent transcript (default)
        conversation_id: Required if current=False
        transcript_path: Optional path if current=False
        guide: If True, return docs on how to find/read transcripts (overrides all)
    """
    if guide:
        return _get_transcript_guide(cwd)

    if current:
        transcript_path, session_id = get_latest_transcript(cwd)
        if not session_id:
            return "❌ No transcript found. Is CLAUDE_HOME set?"
        conversation_id = session_id
    else:
        if not conversation_id:
            return "❌ conversation_id required when current=False"

    if not reason:
        return "❌ reason is required"

    return flag_for_ingestion(
        conversation_id=conversation_id,
        reason=reason,
        priority=priority,
        source="claude_code",
        transcript_path=transcript_path
    )


def get_ingestion_waitlist(
    status_filter: Optional[str] = None,
    min_priority: int = 1
) -> List[WaitlistEntry]:
    """
    Get waitlist entries, optionally filtered.

    Returns list sorted by priority (highest first), then by flagged_at.
    """
    waitlist = load_waitlist()

    entries = list(waitlist.values())

    if status_filter:
        entries = [e for e in entries if e.status == status_filter]

    entries = [e for e in entries if e.priority >= min_priority]

    # Sort: priority desc, then flagged_at asc
    entries.sort(key=lambda e: (-e.priority, e.flagged_at))

    return entries


def update_waitlist_status(
    conversation_id: str,
    status: Literal["pending", "in_progress", "ingested", "skipped"]
) -> str:
    """Update status of a waitlist entry."""
    waitlist = load_waitlist()

    if conversation_id not in waitlist:
        return f"❌ Not in waitlist: {conversation_id}"

    waitlist[conversation_id].status = status
    save_waitlist(waitlist)

    return f"✓ Updated {conversation_id} status to: {status}"


def remove_from_waitlist(conversation_id: str) -> str:
    """Remove a conversation from waitlist entirely."""
    waitlist = load_waitlist()

    if conversation_id not in waitlist:
        return f"❌ Not in waitlist: {conversation_id}"

    del waitlist[conversation_id]
    save_waitlist(waitlist)

    return f"✓ Removed from waitlist: {conversation_id}"


def get_waitlist_stats() -> Dict:
    """Get summary stats for the waitlist."""
    waitlist = load_waitlist()

    by_status = {"pending": 0, "in_progress": 0, "ingested": 0, "skipped": 0}
    by_priority = {i: 0 for i in range(1, 11)}
    by_source = {}

    for entry in waitlist.values():
        by_status[entry.status] = by_status.get(entry.status, 0) + 1
        by_priority[entry.priority] = by_priority.get(entry.priority, 0) + 1
        by_source[entry.source] = by_source.get(entry.source, 0) + 1

    return {
        "total": len(waitlist),
        "by_status": by_status,
        "by_priority": {k: v for k, v in by_priority.items() if v > 0},
        "by_source": by_source
    }
