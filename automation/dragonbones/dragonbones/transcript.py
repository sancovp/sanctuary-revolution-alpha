"""Transcript reading utilities for Dragonbones hook.

Uses conversation_ingestion_mcp.claude_transcript_utils.parse_transcript_file
to parse the full CC transcript jsonl reliably. The previous implementation
(tail-N-lines + manual boundary walk) returned empty text on large transcripts
when the recent tail was dominated by attachment / tool_result entries — the
boundary walker would fail to find a real user message, and the forward scan
through the tail had no text blocks to collect.

Tradeoff: full-file parse costs ~200ms per hook on a 26MB / 16k-line transcript
versus the prior ~tens-of-ms tail read. Accepting this for correctness until
incremental / cached parsing is added.
"""

import os
from typing import List, Set, Tuple

try:
    from conversation_ingestion_mcp.claude_transcript_utils import parse_transcript_file
    _UTILS_AVAILABLE = True
except Exception:
    _UTILS_AVAILABLE = False


def _is_real_user_message(entry_raw: dict) -> bool:
    """Check if a 'user' entry is a real user message (not tool_result attachment)."""
    message = entry_raw.get("message", {})
    content = message.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text", "").strip():
                    return True
    elif isinstance(content, str) and content.strip():
        return True
    return False


def get_last_assistant_text(transcript_path: str) -> Tuple[str, int, List[str], Set[str]]:
    """Read ALL assistant text from current turn + skill/tool calls.

    A 'turn' = all assistant messages since the last real user message.
    Uses claude_transcript_utils.parse_transcript_file for reliable full-file
    parsing. The previous tail-based reader silently returned empty on large
    transcripts whose tail had no real-user-message boundary.

    Returns (text, line_index, skill_calls, tools_called).
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return "", 0, [], set()

    if not _UTILS_AVAILABLE:
        return "", 0, [], set()

    try:
        entries = parse_transcript_file(transcript_path)
    except Exception:
        return "", 0, [], set()

    if not entries:
        return "", 0, [], set()

    # Walk backwards to find the last REAL user message boundary.
    user_boundary = -1
    for idx in range(len(entries) - 1, -1, -1):
        e = entries[idx]
        if e.type == "user" and _is_real_user_message(e.raw):
            user_boundary = idx
            break

    turn_skill_calls: List[str] = []
    turn_tools_called: Set[str] = set()
    all_turn_texts: List[str] = []
    last_idx = 0

    # Scan forward from user boundary, collecting ALL assistant messages in the turn.
    start = max(user_boundary + 1, 0)
    for idx in range(start, len(entries)):
        e = entries[idx]
        if e.type != "assistant":
            continue
        message = e.raw.get("message", {})
        content = message.get("content", [])
        texts: List[str] = []
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    texts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_name = block.get("name", "")
                    if tool_name:
                        turn_tools_called.add(tool_name)
                    if tool_name == "Skill":
                        skill_input = block.get("input", {})
                        skill_name = skill_input.get("skill", "")
                        if skill_name:
                            turn_skill_calls.append(skill_name)
        elif isinstance(content, str) and content.strip():
            texts.append(content)
        msg_text = "\n".join(texts)
        if msg_text.strip():
            all_turn_texts.append(msg_text)
        last_idx = idx

    return "\n".join(all_turn_texts), last_idx, turn_skill_calls, turn_tools_called
