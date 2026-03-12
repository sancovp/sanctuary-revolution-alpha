#!/usr/bin/env python3
# codenose ignore
"""
CodeNose PreToolUse Hook - Architecture Lock Enforcement

Blocks writes to non-canonical filenames when arch lock is enabled.
This runs BEFORE the write happens, so it can actually prevent it.
"""

import json
import sys
import os
import re
from pathlib import Path

ARCH_LOCK_FILE = os.path.expanduser("~/.claude/.codenose_arch_lock")

CANONICAL_FILENAMES = {
    "__init__.py",
    "utils.py",
    "core.py",
    "models.py",
    "mcp_server.py",
    "api.py",
    "cli.py",
    "main.py",
    "config.py",
    "constants.py",
    "types.py",
    "exceptions.py",
}

EXEMPT_DIRS = {"util_deps", "tests", "test", "__pycache__", "migrations", "scripts", "hooks", "commands"}

TEST_PATTERNS = [r"^test_.*\.py$", r"^.*_test\.py$", r"^conftest\.py$"]


def is_arch_locked():
    return os.path.exists(ARCH_LOCK_FILE)


def check_architecture(file_path):
    """Check if file follows canonical architecture naming"""
    path = Path(file_path)
    filename = path.name
    parent_dir = path.parent.name
    path_parts = set(path.parts)

    # Skip non-Python files
    if not filename.endswith('.py'):
        return None

    # Skip exempt directories
    if parent_dir in EXEMPT_DIRS or any(d in path_parts for d in EXEMPT_DIRS):
        return None

    # Skip test files
    for pattern in TEST_PATTERNS:
        if re.match(pattern, filename):
            return None

    # Check if filename is canonical
    if filename not in CANONICAL_FILENAMES:
        return f"'{filename}' is not canonical. Use: utils.py, core.py, models.py, mcp_server.py, api.py, cli.py"

    return None


try:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    # Only check Write/Edit/MultiEdit for Python files
    if tool_name in ["Edit", "Write", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")

        # Only enforce if arch lock is ON
        if is_arch_locked() and file_path.endswith('.py'):
            violation = check_architecture(file_path)

            if violation:
                error_msg = f"""
<codenose>
🔒 ARCH LOCK MODE - BLOCKED 🔒
🏗️=arch

{violation}

📚 Run: equip.exec {{"name": "understand-onion-arch"}} for full architecture guide

To disable lock: rm ~/.claude/.codenose_arch_lock
</codenose>
"""
                print(error_msg, file=sys.stderr)
                sys.exit(2)  # Block the write

    sys.exit(0)

except Exception as e:
    # On error, allow the operation
    sys.exit(0)
