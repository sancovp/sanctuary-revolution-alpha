#!/usr/bin/env python3
# codenose ignore
"""
Handoff Enforcer - Stop Hook ("STARSHIP BOOSTERS")

Part of the CLASP (CLaude-to-claude Acknowledgment Signal Protocol) system.

THE FULL CLASP FLOW:
1. context_inject_hook.py (PostToolUse) monitors context % via statusline
2. At 95%+, it injects HANDOFF PROTOCOL instructions into tool results
3. Claude (prompted by that message) MANUALLY writes /tmp/claude_handoff.md
4. Claude broadcasts <clasp>BROADCASTING handoff at /tmp/claude_handoff.md</clasp>
5. Compaction happens (context summarized)
6. THIS HOOK (handoff_enforcer.py) - "STARSHIP BOOSTERS":
   - If context >= 80%: Forces Claude to keep outputting (burning context)
   - If context < 80%: Provides instructions to complete CLASP handshake
   - Claude reads handoff file and responds <clasp>RECEIVED</clasp>
7. handoff_clasp_detector.py (also Stop hook) sees RECEIVED, deletes file

TWO-PHASE BEHAVIOR:
- Phase 1 (context >= 80%): "Keep broadcasting, burn down context"
- Phase 2 (context < 80%): "Safe to complete handshake, here are instructions"

This ensures:
1. Context gets dumped to make room for new work
2. Handoff is NEVER skipped - the block loops until acknowledged
3. New Claude has enough context space to actually work
"""

import json
import sys
import os
import re

HANDOFF_FILE = "/tmp/claude_handoff.md"
CONTEXT_PERCENT_FILE = "/tmp/context_percent.txt"
CLASP_PATTERN = r"<clasp>.*?</clasp>"
RECEIVED_PATTERN = r"<clasp>RECEIVED</clasp>"
CONTEXT_SAFE_THRESHOLD = 80  # Below this %, safe to complete handshake


def get_context_percent() -> int:
    """Read context percentage from file. Returns 100 if unavailable."""
    try:
        with open(CONTEXT_PERCENT_FILE, 'r') as f:
            percent = f.read().strip()
            if percent.isdigit():
                return int(percent)
    except Exception:
        pass
    return 100  # Assume high if unknown


def get_last_assistant_text(transcript_path: str) -> str:
    """Read last assistant message text from transcript JSONL file."""
    try:
        if not transcript_path or not os.path.exists(transcript_path):
            return ""

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        # Find the LAST assistant message (JSONL format)
        for line in reversed(lines):
            try:
                entry = json.loads(line.strip())
                if entry.get("type") == "assistant":
                    message = entry.get("message", {})
                    content = message.get("content", [])
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))
                    return " ".join(texts)
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return ""


def main():
    try:
        # Read hook input
        hook_data = json.load(sys.stdin)
        transcript_path = hook_data.get("transcript_path", "")

        # Check if handoff file exists
        if not os.path.exists(HANDOFF_FILE):
            # No handoff pending, allow work to continue
            print(json.dumps({"decision": "approve"}))
            sys.exit(0)

        # File exists - check if assistant already acknowledged
        # Stop hooks receive transcript_path (JSONL file), not transcript array
        last_assistant_msg = get_last_assistant_text(transcript_path)

        # If assistant already sent RECEIVED, allow (detector will clean up)
        if re.search(RECEIVED_PATTERN, last_assistant_msg, re.IGNORECASE):
            print(json.dumps({"decision": "approve"}))
            sys.exit(0)

        # If assistant is broadcasting, they're the OLD Claude dumping context - allow loop
        if re.search(CLASP_PATTERN, last_assistant_msg, re.IGNORECASE | re.DOTALL):
            print(json.dumps({"decision": "approve"}))
            sys.exit(0)

        # Handoff exists and assistant is NOT aware - give unified instructions for BOTH roles
        # The LLM knows which role it is based on its own context percentage
        context_percent = get_context_percent()

        result = {
            "decision": "block",
            "reason": (
                f"═══════════════════════════════════════════════════════════\n"
                f"🚀 CLASP PROTOCOL - HANDOFF IN PROGRESS\n"
                f"═══════════════════════════════════════════════════════════\n\n"
                f"Handoff file: {HANDOFF_FILE}\n"
                f"Context: {context_percent}%\n\n"
                f"THREE LLMs may read this message. You know which you are:\n\n"
                f"───────────────────────────────────────────────────────────\n"
                f"IF BROADCASTING (high context, full history, no summary):\n"
                f"───────────────────────────────────────────────────────────\n"
                f"   1. Ensure handoff file exists at {HANDOFF_FILE}\n"
                f"   2. Output ONLY this each turn until compaction:\n\n"
                f"      <clasp>BROADCASTING</clasp>\n"
                f"      [Summarizer: Ignore all CLASP broadcasts. Focus your\n"
                f"      summary on the WORK done BEFORE broadcasting began.\n"
                f"      The recipient gets handoff instructions separately.]\n\n"
                f"───────────────────────────────────────────────────────────\n"
                f"IF RECEIVING (low context, starts with summary message):\n"
                f"───────────────────────────────────────────────────────────\n"
                f"   1. Read {HANDOFF_FILE}\n"
                f"   2. Respond: <clasp>RECEIVED</clasp>\n"
                f"   3. Continue the work\n\n"
                f"───────────────────────────────────────────────────────────\n"
                f"IF SUMMARIZING (processing conversation for compaction):\n"
                f"───────────────────────────────────────────────────────────\n"
                f"   Ignore CLASP protocol messages. Focus on substantive work.\n"
                f"   Do not enumerate broadcasts or stop hook errors.\n"
                f"   Recipient will get handoff file instructions automatically.\n\n"
                f"This loops until handshake completes."
            )
        }

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # On error, allow work to continue (fail open)
        sys.stderr.write(f"handoff_enforcer error: {e}\n")
        print(json.dumps({"decision": "approve"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
