#!/usr/bin/env python3
"""SkillLog v2 hook - parses typed SkillLog entries and handles skill matching/queueing.

Format: 🎯 STATUS::domain::subdomain::skill_name 🎯

STATUS types:
- PREDICTED: LLM thinks this skill exists, check and inject if found
- NEEDED: LLM needs this skill, not sure if exists, check and inject if found
- FOUND: LLM knows this exists (already checked), just inject
- NOT_FOUND: LLM checked, doesn't exist, queue for creation
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from skill_manager.core import SkillManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Queue file for skills that need to be created
SKILL_CREATION_QUEUE = Path.home() / ".claude" / "skill_creation_queue.json"

VALID_STATUSES = {"PREDICTED", "NEEDED", "FOUND", "NOT_FOUND"}


def parse_skilllog(text: str) -> list[dict]:
    """Extract all SkillLog entries from text.

    Format: 🎯 STATUS::domain::subdomain::skill_name 🎯
    Also supports legacy format: 🎯 domain::subdomain::skill_name 🎯 (treated as PREDICTED)

    Returns list of dicts with status and path.
    """
    pattern = r'🎯\s*([^🎯]+)\s*🎯'
    matches = re.findall(pattern, text)

    entries = []
    for match in matches:
        match = match.strip()
        parts = match.split("::")

        # Check if first part is a status
        if parts and parts[0].upper() in VALID_STATUSES:
            status = parts[0].upper()
            path = "::".join(parts[1:])
        else:
            # Legacy format - treat as PREDICTED
            status = "PREDICTED"
            path = match

        entries.append({"status": status, "path": path, "raw": match})

    return entries


def load_creation_queue() -> list[dict]:
    """Load the skill creation queue from disk."""
    if SKILL_CREATION_QUEUE.exists():
        try:
            return json.loads(SKILL_CREATION_QUEUE.read_text())
        except (json.JSONDecodeError, IOError):
            logger.exception("Failed to load creation queue")
            return []
    return []


def save_creation_queue(queue: list[dict]):
    """Save the skill creation queue to disk."""
    SKILL_CREATION_QUEUE.write_text(json.dumps(queue, indent=2))


def add_to_creation_queue(path: str):
    """Add a skill path to the creation queue."""
    queue = load_creation_queue()

    # Check if already in queue
    existing_paths = {item["path"] for item in queue}
    if path not in existing_paths:
        queue.append({
            "path": path,
            "added": datetime.now().isoformat(),
            "created": False
        })
        save_creation_queue(queue)
        logger.info(f"Added to creation queue: {path}")
        return True
    return False


def get_last_assistant_text(transcript: list) -> str:
    """Extract text from most recent assistant message."""
    for msg in reversed(transcript):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        for block in content:
            if block.get("type") == "text":
                return block.get("text", "")
    return ""


def format_not_found_entry(path: str, queued: bool) -> str:
    """Format output for NOT_FOUND status."""
    msg = "Queued for creation" if queued else "Already in creation queue"
    return f"🎯 [NOT_FOUND] {path}\n  → {msg}"


def format_found_entry(path: str, has_match: bool) -> str:
    """Format output for FOUND status."""
    if has_match:
        return f"🎯 [FOUND] {path}\n  → ✅ Injecting skill"
    return f"🎯 [FOUND] {path}\n  → ⚠️ Marked FOUND but not in catalog - queued"


def format_predicted_entry(entry: dict, result: dict) -> str:
    """Format output for PREDICTED/NEEDED status."""
    lines = [f"🎯 [{entry['status']}] {entry['path']}"]

    if result and result.get('has_match'):
        lines.append("  → ✅ FOUND - matches available:")
        for m in result['matches'][:3]:
            domain_path = f"{m['domain']}::{m['subdomain']}" if m['subdomain'] else m['domain']
            lines.append(f"     - {m['name']} ({domain_path}) [score: {m['score']:.2f}]")
    else:
        lines.append("  → ❌ NOT_FOUND - queued for creation")

    return "\n".join(lines)


def process_entry(entry: dict, manager: SkillManager) -> str:
    """Process a single SkillLog entry and return formatted output."""
    status = entry["status"]
    path = entry["path"]

    if status == "NOT_FOUND":
        queued = add_to_creation_queue(path)
        return format_not_found_entry(path, queued)

    # For FOUND/PREDICTED/NEEDED, check the catalog
    result = manager.match_skilllog(path)
    has_match = result and result.get('has_match')

    if status == "FOUND":
        if not has_match:
            add_to_creation_queue(path)
        return format_found_entry(path, has_match)

    # PREDICTED or NEEDED
    if not has_match:
        add_to_creation_queue(path)
    return format_predicted_entry(entry, result)


def main():
    """Hook entry point."""
    input_data = json.load(sys.stdin)
    transcript = input_data.get("transcript", [])

    assistant_text = get_last_assistant_text(transcript)
    if not assistant_text:
        logger.debug("No assistant message found")
        sys.exit(0)

    entries = parse_skilllog(assistant_text)
    if not entries:
        logger.debug("No SkillLog found in response")
        sys.exit(0)

    manager = SkillManager()
    outputs = [process_entry(entry, manager) for entry in entries]

    output = "\n\n".join(outputs)
    logger.info(f"SkillLog v2 processed {len(entries)} entries")
    sys.stdout.write(json.dumps({"result": output}))


if __name__ == "__main__":
    main()
