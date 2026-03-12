#!/usr/bin/env python3
# codenose ignore
"""
Handoff CLASP Detector - Stop Hook

Part of the CLASP (CLaude-to-claude Acknowledgment Signal Protocol) system.

THE FULL CLASP FLOW:
1. context_inject_hook.py (PostToolUse) monitors context % via statusline
2. At 95%+, it injects HANDOFF PROTOCOL instructions into tool results
3. Claude (prompted by that message) MANUALLY writes /tmp/claude_handoff.md
4. Claude broadcasts <clasp>BROADCASTING handoff at /tmp/claude_handoff.md</clasp>
5. Compaction happens (context summarized)
6. handoff_enforcer.py (Stop hook) blocks NEW Claude from working until they:
   - Read the handoff file
   - Respond with <clasp>RECEIVED</clasp>
7. THIS HOOK (handoff_clasp_detector.py) sees RECEIVED, deletes file, handshake complete

IMPORTANT: This MUST be a Stop hook, not UserPromptSubmit!
At UserPromptSubmit time, Claude hasn't responded yet.
At Stop time, the assistant response is in the transcript (JSONL file).
"""

import json
import sys
import os
import re

HANDOFF_FILE = "/tmp/claude_handoff.md"
RECEIVED_PATTERN = r"<clasp>RECEIVED</clasp>"


def check_received_in_transcript(transcript_path: str) -> bool:
    """Check if LAST assistant message contains <clasp>RECEIVED</clasp>."""
    try:
        if not transcript_path or not os.path.exists(transcript_path):
            return False

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        # Find the LAST assistant message only (JSONL format)
        last_assistant_line = None
        for line in reversed(lines):
            try:
                entry = json.loads(line.strip())
                if entry.get("type") == "assistant":
                    last_assistant_line = entry
                    break
            except json.JSONDecodeError:
                continue

        if not last_assistant_line:
            return False

        # Check only the last assistant message for <clasp>RECEIVED</clasp>
        message = last_assistant_line.get("message", {})
        content = message.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if re.search(RECEIVED_PATTERN, text, re.IGNORECASE):
                    return True
    except Exception:
        pass
    return False


def main():
    try:
        # Read hook input
        hook_data = json.load(sys.stdin)
        transcript_path = hook_data.get("transcript_path", "")

        # Check if handoff file exists - if not, nothing to do
        if not os.path.exists(HANDOFF_FILE):
            print(json.dumps({"decision": "approve"}))
            sys.exit(0)

        # Check for RECEIVED in transcript
        if check_received_in_transcript(transcript_path):
            os.remove(HANDOFF_FILE)
            # Approve stop - handshake complete
            print(json.dumps({"decision": "approve"}))
            sys.exit(0)

        # Handoff exists but no RECEIVED - let handoff_enforcer handle blocking
        print(json.dumps({"decision": "approve"}))
        sys.exit(0)

    except Exception as e:
        # On error, approve (fail open)
        print(json.dumps({"decision": "approve"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
