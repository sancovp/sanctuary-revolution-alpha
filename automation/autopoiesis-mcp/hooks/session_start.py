#!/usr/bin/env python3
"""
SessionStart hook - Rehydration workflow.

On session start:
A) Check pruning status
B) Read MEMORY.md and enforce rules
C) Prune if needed
D) Output rehydration context to agent
"""
import json
import sys
import subprocess
from pathlib import Path

MEMORY_PATH = Path("/home/GOD/.claude/projects/-home-GOD/memory/MEMORY.md")

def check_prune_needed():
    """Check if pruning is needed."""
    try:
        result = subprocess.run(
            ["python3", str(Path.home() / ".claude/scripts/prune-memory.py"), "stats"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except Exception as e:
        return f"Error checking prune status: {e}"

def read_memory():
    """Read MEMORY.md and validate format."""
    if not MEMORY_PATH.exists():
        return "MEMORY.md not found"

    content = MEMORY_PATH.read_text()
    lines = content.split('\n')

    # Check for violations (anything beyond concept names + Why statements)
    violations = []
    for i, line in enumerate(lines, 1):
        if any(marker in line.lower() for marker in ['done', 'status', 'file path', '✅', '❌', 'todo', 'task']):
            if not line.startswith('#') and not line.startswith('Why:'):
                violations.append(f"Line {i}: {line[:80]}")

    return {
        'content': content,
        'line_count': len(lines),
        'violations': violations
    }

def main():
    """Hook entry point."""
    prune_status = check_prune_needed()
    memory_data = read_memory()

    output = []

    # A) Pruning check
    output.append("=== REHYDRATION WORKFLOW ===\n")
    output.append("A) PRUNE STATUS:")
    output.append(prune_status)
    output.append("")

    # B) Memory validation
    output.append("B) MEMORY.md STATUS:")
    if isinstance(memory_data, str):
        output.append(memory_data)
    else:
        output.append(f"Lines: {memory_data['line_count']}")
        if memory_data['violations']:
            output.append("\n⚠️ MEMORY.md VIOLATIONS DETECTED:")
            output.append("These lines contain content that should be in CartON, not MEMORY.md:")
            for v in memory_data['violations'][:5]:  # Show first 5
                output.append(f"  {v}")
            output.append("\nFIX IMMEDIATELY: Remove all content except concept names + Why statements")
        else:
            output.append("✓ Format valid (concept names + Why only)")
    output.append("")

    # C) BML entry point
    output.append("C) REQUIRED: Use /rehydrate-from-memory then /bml-mission-loop-e2e. If you don't see both skills, equip persona gnosys first.")
    output.append("")

    print('\n'.join(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
