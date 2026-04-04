"""Transcript reading utilities for Dragonbones hook."""

import json
import os


def get_last_assistant_text(transcript_path: str) -> tuple[str, int, list[str], set[str]]:
    """Read last assistant message text + ALL skill/tool calls from the current turn.

    A 'turn' = all assistant messages since the last user message.

    Returns (text, line_index, skill_calls, tools_called).
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return "", 0, [], set()

    with open(transcript_path, 'r') as f:
        lines = f.readlines()

    turn_skill_calls = []
    turn_tools_called = set()
    last_text = ""
    last_idx = 0

    # Walk backwards to find the last user message boundary
    user_boundary = -1
    for idx in range(len(lines) - 1, -1, -1):
        try:
            entry = json.loads(lines[idx].strip())
            if entry.get("type") == "human":
                user_boundary = idx
                break
        except json.JSONDecodeError:
            continue

    # Scan forward from user boundary, collecting all assistant messages
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
                last_text = "\n".join(texts)
                last_idx = idx
        except json.JSONDecodeError:
            continue

    return last_text, last_idx, turn_skill_calls, turn_tools_called
