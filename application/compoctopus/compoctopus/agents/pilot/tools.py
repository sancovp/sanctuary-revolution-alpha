"""Pilot hooks — BEFORE_TOOL_CALL hook that blocks write operations."""

import re
from typing import Optional


# Patterns that indicate file modification
WRITE_PATTERNS = [
    r'\b(cat|echo|printf)\s+.*\s*[^2&\d]>',  # cat/echo redirect (not 2>&1)
    r'\btee\b',                            # tee (writes to files)
    r'\bsed\s+-i',                         # sed in-place
    r'\b(cp|mv|rm|mkdir|touch|chmod|chown)\b',  # file operations
    r'\bgit\s+(add|commit|push|merge|rebase|reset|checkout\s+-b)',  # git write ops
    r">>",                                 # append redirect
    r'\bpython3?\s+.*-c\s+.*(?:open|write|Path.*write)',  # python file writes
    r'\bpip\b',                            # no installing packages
    r'\bcurl\b.*-o',                       # no downloading files
    r'\bwget\b',                           # no downloading
]

# Allowed write patterns (exceptions) — ONLY these can write
ALLOWED_PATTERNS = [
    r'bash\s+/tmp/compoctopus_repo/scripts/run_ralph\.sh',  # ralph dispatch
    r'gh\s+pr\s+(create|merge|close|comment)',               # gh PR operations
    r'>\s*/tmp/pilot_reqs/',                                  # writing reqs docs
    r'cat\s+.*>\s*/tmp/pilot_reqs/',                         # cat to reqs
    r'echo\s+.*>\s*/tmp/pilot_reqs/',                        # echo to reqs
    r'tee\s+/tmp/pilot_reqs/',                               # tee to reqs
    r'mkdir\s+-p\s+/tmp/pilot_reqs',                         # mkdir for reqs
    r'python3?\s+-c\s+.*pilot_queue/done',                   # writing done signal
    r'>\s*/tmp/heaven_data/',                                 # writing to heaven data (CA cache etc)
    r'cat\s+.*>\s*/tmp/heaven_data/',                        # cat to heaven data
    r'mkdir\s+-p\s+/tmp/heaven_data/',                       # mkdir heaven data
    r'mkdir\s+-p\s+/tmp/ralph',                              # mkdir for ralph worktrees
]


def check_pilot_bash_command(command: str) -> Optional[str]:
    """Returns block reason if command is a write op, else None."""
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command):
            return None

    for pattern in WRITE_PATTERNS:
        if re.search(pattern, command):
            return (
                f"BLOCKED: You are a Starship Pilot — you NEVER write code or "
                f"modify files. Only ralph writes code. Write requirements to "
                f"/tmp/pilot_reqs/ and dispatch ralph via run_ralph.sh."
            )
    return None


def pilot_before_tool_call(ctx):
    """BEFORE_TOOL_CALL hook for pilot agents. Replaces write commands with block message."""
    if ctx.tool_name != "BashTool":
        return

    command = ""
    if ctx.tool_args:
        if isinstance(ctx.tool_args, dict):
            command = ctx.tool_args.get("command", "")
        elif isinstance(ctx.tool_args, str):
            command = ctx.tool_args

    if not command:
        return

    blocked = check_pilot_bash_command(command)
    if blocked:
        # Replace the command with an echo of the block message
        # This way the tool still "runs" but returns the error to the model
        if isinstance(ctx.tool_args, dict):
            ctx.tool_args["command"] = f"echo 'ERROR: {blocked}' >&2; exit 1"
        else:
            ctx.tool_args = f"echo 'ERROR: {blocked}' >&2; exit 1"
