#!/usr/bin/env python3
"""
CartON PreCompact Hook - Auto-capture conversation transcripts
Converts Claude conversation transcripts to CartON concepts via queue

HOOK CONFIGURATION (ADD TO /home/GOD/.claude/settings.local.json):

"PreCompact": [
  {
    "matcher": "manual",
    "hooks": [
      {
        "type": "command",
        "command": "python3 /home/GOD/.claude/hooks/carton_precompact.py"
      }
    ]
  },
  {
    "matcher": "auto",
    "hooks": [
      {
        "type": "command",
        "command": "python3 /home/GOD/.claude/hooks/carton_precompact.py"
      }
    ]
  }
]
"""

import json
import os
import re
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path


def extract_text_from_message(msg):
    """Extract text content from Claude transcript message format."""
    message_content = msg.get('message', {})
    content_items = message_content.get('content', [])

    text_parts = []
    for item in content_items:
        if isinstance(item, dict) and item.get('type') == 'text':
            text_parts.append(item.get('text', ''))
        elif isinstance(item, str):
            text_parts.append(item)

    return ''.join(text_parts)


def extract_tool_uses_from_message(msg):
    """Extract tool use blocks from Claude transcript message format."""
    message_content = msg.get('message', {})
    content_items = message_content.get('content', [])

    tool_uses = []
    for item in content_items:
        if isinstance(item, dict) and item.get('type') == 'tool_use':
            tool_uses.append({
                'name': item.get('name', 'unknown'),
                'input': item.get('input', {})
            })

    return tool_uses


def parse_jsonl_transcript(transcript_path):
    """Parse JSONL transcript file into messages"""
    messages = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        msg = json.loads(line.strip())
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError as e:
        print(f"Error: Transcript file not found: {transcript_path}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return []

    messages.sort(key=lambda x: x.get('timestamp', ''))
    return messages


def get_last_processed_index(tracking_dir: Path, session_id: str) -> int:
    """Get the last processed message index for this session."""
    tracking_file = tracking_dir / f"{session_id}.json"
    if tracking_file.exists():
        try:
            with open(tracking_file, 'r') as f:
                data = json.load(f)
                return data.get('last_processed_idx', -1)
        except (json.JSONDecodeError, IOError) as e:
            traceback.print_exc()
            return -1
    return -1


def save_last_processed_index(tracking_dir: Path, session_id: str, idx: int):
    """Save the last processed message index for this session."""
    tracking_file = tracking_dir / f"{session_id}.json"
    with open(tracking_file, 'w') as f:
        json.dump({
            'last_processed_idx': idx,
            'updated_at': datetime.now().isoformat()
        }, f)


if __name__ == "__main__":
    log_file = "/home/GOD/.claude/hooks/carton_precompact.log"
    queue_dir = Path("/tmp/heaven_data/carton_queue")
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Tracking directory for incremental processing
    tracking_dir = Path("/tmp/heaven_data/carton_precompact_tracking")
    tracking_dir.mkdir(parents=True, exist_ok=True)

    with open(log_file, "w") as f:
        f.write(f"{datetime.now().isoformat()}: carton_precompact.py started\n")

    # Read hook data from stdin
    raw_stdin = sys.stdin.read()
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}: RAW STDIN: {raw_stdin[:500]}\n")

    try:
        hook_data = json.loads(raw_stdin)
    except json.JSONDecodeError as e:
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: JSON decode error: {e}\n{traceback.format_exc()}\n")
        sys.exit(1)

    session_id = hook_data.get('session_id')
    transcript_path = hook_data.get('transcript_path')

    if not session_id or not transcript_path:
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: Missing session_id or transcript_path\n")
        sys.exit(1)

    # Parse transcript
    messages = parse_jsonl_transcript(transcript_path)
    if not messages:
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: No messages in transcript\n")
        sys.exit(0)

    # Get last processed index for incremental processing
    last_processed_idx = get_last_processed_index(tracking_dir, session_id)

    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}: Last processed idx: {last_processed_idx}, Total messages: {len(messages)}\n")

    # Skip if nothing new
    if last_processed_idx >= len(messages) - 1:
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: No new messages to process\n")
        sys.exit(0)

    date_str = datetime.now().strftime("%Y_%m_%d")
    day_concept_name = f"Day_{date_str}"
    timeline_instance_name = f"Raw_Conversation_Timeline_{date_str}"
    conversation_concept_name = f"Conversation_{session_id}"

    queued_count = 0

    # Only queue timeline/conversation concepts on first run for this session
    if last_processed_idx == -1:
        # Queue timeline instance concept
        queue_file = queue_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_timeline.json"
        with open(queue_file, 'w') as f:
            json.dump({
                "raw_concept": True,
                "concept_name": timeline_instance_name,
                "description": f"Raw conversation timeline for {date_str}",
                "relationships": [
                    {"relationship": "is_a", "related": ["Raw_Conversation_Timeline"]},
                    {"relationship": "part_of", "related": [day_concept_name]}
                ]
            }, f)
        queued_count += 1

        # Queue conversation concept
        queue_file = queue_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_conv.json"
        with open(queue_file, 'w') as f:
            json.dump({
                "raw_concept": True,
                "concept_name": conversation_concept_name,
                "description": f"Claude Code conversation from session {session_id}",
                "relationships": [
                    {"relationship": "is_a", "related": ["Conversation"]},
                    {"relationship": "part_of", "related": [timeline_instance_name]},
                    {"relationship": "has_type", "related": ["Claude_Code_Session"]}
                ]
            }, f)
        queued_count += 1

    # Track the highest index we process
    max_processed_idx = last_processed_idx

    # Queue each NEW message as a concept (skip already processed)
    for idx, msg in enumerate(messages):
        # Skip already processed messages
        if idx <= last_processed_idx:
            continue
        if msg.get('isCompactSummary') or msg.get('isMeta'):
            continue

        msg_type = msg.get('type')

        if msg_type == 'user':
            full_content = extract_text_from_message(msg)
            content = full_content[:200]
            concept_name = f"UserThought_{session_id}_{idx}"
            relationships = [
                {"relationship": "is_a", "related": ["User_Thought"]},
                {"relationship": "part_of", "related": [conversation_concept_name]},
                {"relationship": "has_type", "related": ["User_Message"]}
            ]

            queue_file = queue_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_msg{idx}.json"
            with open(queue_file, 'w') as f:
                json.dump({
                    "raw_concept": True,
                    "concept_name": concept_name,
                    "description": content or "User message",
                    "relationships": relationships
                }, f)
            queued_count += 1

        elif msg_type == 'assistant':
            full_content = extract_text_from_message(msg)
            content = full_content[:200]
            concept_name = f"AgentMessage_{session_id}_{idx}"
            relationships = [
                {"relationship": "is_a", "related": ["Agent_Message"]},
                {"relationship": "part_of", "related": [conversation_concept_name]},
                {"relationship": "has_type", "related": ["Assistant_Response"]}
            ]

            queue_file = queue_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_msg{idx}.json"
            with open(queue_file, 'w') as f:
                json.dump({
                    "raw_concept": True,
                    "concept_name": concept_name,
                    "description": content or "Assistant message",
                    "relationships": relationships
                }, f)
            queued_count += 1

            # Queue CogLog entries - match 🧠 content 🧠 (multiline) or 🧠 content\n (single line)
            brain_pattern = re.compile(r'🧠\s*(.+?)🧠|🧠\s*(.+?)(?:\n|$)', re.DOTALL)
            coglog_matches = brain_pattern.findall(full_content)
            for coglog_idx, match_tuple in enumerate(coglog_matches):
                # findall returns tuples due to alternation - take whichever group matched
                semantic_addr = (match_tuple[0] or match_tuple[1]).strip()
                if not semantic_addr:
                    continue

                coglog_concept_name = f"CogLog_{session_id}_{idx}_{coglog_idx}"
                coglog_relationships = [
                    {"relationship": "is_a", "related": ["Cog_Log_Entry"]},
                    {"relationship": "part_of", "related": [conversation_concept_name, concept_name]},
                ]

                # CogLog is emergent - no domain mapping, but DO track type for querying
                if semantic_addr.startswith('file::'):
                    coglog_relationships.append({"relationship": "is_a", "related": ["File_CogLog"]})
                else:
                    coglog_relationships.append({"relationship": "is_a", "related": ["General_CogLog"]})

                queue_file = queue_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_coglog{idx}_{coglog_idx}.json"
                with open(queue_file, 'w') as f:
                    json.dump({
                        "raw_concept": True,
                        "concept_name": coglog_concept_name,
                        "description": semantic_addr,
                        "relationships": coglog_relationships
                    }, f)
                queued_count += 1

            # Queue tool calls
            tool_uses = extract_tool_uses_from_message(msg)
            for tool_idx, tool_use in enumerate(tool_uses):
                raw_tool_name = tool_use.get('name', 'unknown')

                if raw_tool_name == 'mcp__strata__execute_action':
                    tool_input = tool_use.get('input', {})
                    server_name = tool_input.get('server_name', '')
                    action_name = tool_input.get('action_name', '')
                    if server_name and action_name:
                        tool_name = f"mcp__{server_name}__{action_name}"
                    else:
                        tool_name = raw_tool_name
                else:
                    tool_name = raw_tool_name

                tool_concept_name = f"ToolCall_{session_id}_{idx}_{tool_idx}"
                tool_relationships = [
                    {"relationship": "is_a", "related": ["Tool_Call_Message"]},
                    {"relationship": "part_of", "related": [concept_name]},
                    {"relationship": "has_type", "related": [f"Tool_{tool_name}"]}
                ]

                queue_file = queue_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_tool{idx}_{tool_idx}.json"
                with open(queue_file, 'w') as f:
                    json.dump({
                        "raw_concept": True,
                        "concept_name": tool_concept_name,
                        "description": f"Tool call: {tool_name}",
                        "relationships": tool_relationships
                    }, f)
                queued_count += 1

        # Track highest processed index
        max_processed_idx = idx

    # Save progress for incremental processing
    save_last_processed_index(tracking_dir, session_id, max_processed_idx)

    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}: Queued {queued_count} NEW concepts for {session_id} (processed up to idx {max_processed_idx})\n")

    sys.exit(0)
