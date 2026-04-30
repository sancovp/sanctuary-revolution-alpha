#!/usr/bin/env python3
# codenose ignore
"""
CodeNose v2 PostToolUse Hook - Thin wrapper using codenose library.

Detects code smells after Edit/Write/MultiEdit operations.
All logic delegated to the codenose library.
"""
import json
import os
import sys
import time
from pathlib import Path

try:
    from codenose import CodeNose
except ImportError:
    # Library not installed, exit silently
    sys.exit(0)

CA_QUEUE_DIR = Path("/tmp/ca_refresh_queue")
CA_MCP_DIR = Path("/home/GOD/gnosys-plugin-v2/knowledge/context-alignment/neo4j_codebase_mcp")


def _queue_ca_refresh(file_path: str):
    """Append touched file to per-codebase CA refresh queue."""
    p = Path(file_path).resolve()
    # Walk up to find repo root (.git or .claude)
    repo_root = None
    for parent in [p] + list(p.parents):
        if (parent / ".git").exists() or (parent / ".claude").exists():
            repo_root = parent
            break
    if not repo_root:
        return
    slug = repo_root.name
    CA_QUEUE_DIR.mkdir(exist_ok=True)
    queue_file = CA_QUEUE_DIR / f"{slug}.jsonl"
    entry = json.dumps({"file": str(p), "time": time.time()})
    with open(queue_file, "a") as f:
        f.write(entry + "\n")

    # Attempt background flush of any stale queues (5min debounce checked inside)
    _try_flush_stale_queues()


def _try_flush_stale_queues():
    """Spawn background subprocess to flush stale CA refresh queues."""
    import subprocess
    if not CA_QUEUE_DIR.exists():
        return
    # Fire and forget — flush_ca_queue checks debounce internally
    subprocess.Popen(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); "
         "from pattern_detector import flush_ca_queue; "
         "r = flush_ca_queue(); "
         "f = r.get('flushed', []); "
         "[__import__('sys').stderr.write("
         "'CA refresh: %%s (%%d patterns)\\n' %% (x['repo'], x.get('patterns_found', 0))"
         ") for x in f]" % str(CA_MCP_DIR)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})

        if tool_name not in ["Edit", "Write", "MultiEdit"]:
            sys.exit(0)

        file_path = tool_input.get("file_path", "")
        if not file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c')):
            sys.exit(0)

        # Queue for CA refresh (always, regardless of smells)
        if file_path.endswith('.py'):
            _queue_ca_refresh(file_path)

        # Use the library
        nose = CodeNose()
        result = nose.scan_file(file_path)

        if not result.smells:
            sys.exit(0)

        # Check for critical smells
        has_critical = any(s.critical for s in result.smells)

        # Check arch lock for architecture violations
        if nose.is_arch_locked():
            arch_smells = [s for s in result.smells if s.type == "arch"]
            if arch_smells:
                for s in arch_smells:
                    s.critical = True
                has_critical = True

        # Check TDD mode - coverage warnings become CRITICAL
        if nose.is_tdd_mode():
            coverage_smells = [s for s in result.smells if s.type == "coverage"]
            if coverage_smells:
                for s in coverage_smells:
                    s.critical = True
                    s.msg = f"[TDD MODE] {s.msg}"
                has_critical = True

        # Format and output
        output = nose.format_output(result)
        if output:
            print(output, file=sys.stderr)

        # Exit codes: 0=ok, 2=critical
        sys.exit(2 if has_critical else 0)

    except Exception as e:
        print(f"CodeNose error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
