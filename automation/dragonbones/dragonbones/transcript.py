"""Transcript reading utilities for Dragonbones hook."""

import json
import os


def _read_tail_lines(filepath: str, max_lines: int = 2000) -> list[str]:
    """Read last N lines of a file efficiently using seek from end."""
    try:
        with open(filepath, 'rb') as f:
            f.seek(0, 2)  # End of file
            size = f.tell()
            # Read chunks from end until we have enough lines
            chunk_size = min(size, max_lines * 2000)  # ~2KB per line estimate
            f.seek(max(0, size - chunk_size))
            data = f.read().decode('utf-8', errors='replace')
            lines = data.split('\n')
            # Drop partial first line if we didn't start at beginning
            if size > chunk_size:
                lines = lines[1:]
            return [l + '\n' for l in lines if l.strip()]
    except Exception:
        return []


def _is_real_user_message(entry: dict) -> bool:
    """Check if a 'user' entry is a real user message (not tool_result)."""
    message = entry.get("message", {})
    content = message.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text", "").strip():
                    return True
    elif isinstance(content, str) and content.strip():
        return True
    return False


def get_last_assistant_text(transcript_path: str) -> tuple[str, int, list[str], set[str]]:
    """Read ALL assistant text from current turn + skill/tool calls.

    A 'turn' = all assistant messages since the last real user message.
    Only reads tail of transcript (last 2000 lines) for performance.

    Returns (text, line_index, skill_calls, tools_called).
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return "", 0, [], set()

    lines = _read_tail_lines(transcript_path, max_lines=2000)
    if not lines:
        return "", 0, [], set()

    turn_skill_calls = []
    turn_tools_called = set()
    all_turn_texts = []
    last_idx = 0

    # Walk backwards to find the last REAL user message boundary
    # "user" type entries include tool_results — skip those
    user_boundary = -1
    for idx in range(len(lines) - 1, -1, -1):
        try:
            entry = json.loads(lines[idx].strip())
            if entry.get("type") == "user" and _is_real_user_message(entry):
                user_boundary = idx
                break
        except json.JSONDecodeError:
            continue

    # Scan forward from user boundary, collecting ALL assistant messages in the turn
    start = max(user_boundary + 1, 0)
    for idx in range(start, len(lines)):
        try:
            entry = json.loads(lines[idx].strip())
            if entry.get("type") == "assistant":
                message = entry.get("message", {})
                content = message.get("content", [])
                texts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            texts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name:
                                turn_tools_called.add(tool_name)
                            if tool_name == "Skill":
                                skill_input = block.get("input", {})
                                skill_name = skill_input.get("skill", "")
                                if skill_name:
                                    turn_skill_calls.append(skill_name)
                msg_text = "\n".join(texts)
                if msg_text.strip():
                    all_turn_texts.append(msg_text)
                last_idx = idx
        except json.JSONDecodeError:
            continue

    return "\n".join(all_turn_texts), last_idx, turn_skill_calls, turn_tools_called
