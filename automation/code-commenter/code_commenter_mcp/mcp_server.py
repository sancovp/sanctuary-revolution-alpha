#!/usr/bin/env python3
"""
Code Commenter MCP — comment out / uncomment lines in files.

Tracks commented blocks by content (not line numbers) so uncommenting
works even after the file has been edited and lines have shifted.

Tools:
  comment_out(file_path, start_line, end_line, prefix_comment, suffix_comment)
  uncomment(file_path, start_line, end_line)
"""

import json
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("code-commenter")

LEDGER_PATH = Path("/tmp/code_commenter_ledger.json")

# Map file extensions to comment syntax
COMMENT_SYNTAX = {
    ".py": "#", ".js": "//", ".ts": "//", ".tsx": "//", ".jsx": "//",
    ".java": "//", ".c": "//", ".cpp": "//", ".h": "//", ".go": "//",
    ".rs": "//", ".rb": "#", ".sh": "#", ".bash": "#", ".zsh": "#",
    ".yaml": "#", ".yml": "#", ".toml": "#", ".r": "#", ".pl": "#",
    ".pm": "#", ".lua": "--", ".sql": "--", ".hs": "--", ".elm": "--",
    ".html": "<!--", ".xml": "<!--", ".css": "/*", ".scss": "//",
    ".less": "//", ".md": "<!--",
}

COMMENT_SUFFIX = {
    ".html": "-->", ".xml": "-->", ".css": "*/", ".md": "-->",
}


def _get_comment_chars(file_path: str) -> tuple[str, str]:
    ext = Path(file_path).suffix.lower()
    return COMMENT_SYNTAX.get(ext, "#"), COMMENT_SUFFIX.get(ext, "")


def _load_ledger() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return {}


def _save_ledger(ledger: dict):
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


@mcp.tool()
def comment_out(
    file_path: str,
    start_line: int,
    end_line: int,
    prefix_comment: str = "",
    suffix_comment: str = "",
) -> str:
    """Comment out lines in a file.

    Args:
        file_path: Absolute path to the file.
        start_line: First line to comment (1-indexed).
        end_line: Last line to comment (1-indexed, inclusive).
        prefix_comment: Optional comment to insert BEFORE the commented block.
        suffix_comment: Optional comment to insert AFTER the commented block.

    Returns:
        Summary of what was done.
    """
    p = Path(file_path)
    if not p.exists():
        return f"ERROR: File not found: {file_path}"

    lines = p.read_text().splitlines(keepends=True)
    total = len(lines)

    if start_line < 1 or end_line < 1:
        return "ERROR: Line numbers must be >= 1"
    if start_line > total or end_line > total:
        return f"ERROR: File has {total} lines, requested {start_line}-{end_line}"
    if start_line > end_line:
        return "ERROR: start_line must be <= end_line"

    comment_char, comment_suffix = _get_comment_chars(file_path)

    # Build the commented block as a string
    commented_lines = []

    if prefix_comment:
        commented_lines.append(f"{comment_char} {prefix_comment}\n")

    for i in range(start_line - 1, end_line):
        line = lines[i]
        stripped = line.rstrip("\n\r")
        if stripped.strip() == "":
            commented_lines.append(line)
        else:
            leading = len(stripped) - len(stripped.lstrip())
            whitespace = stripped[:leading]
            code = stripped[leading:]
            if comment_suffix:
                commented_lines.append(f"{whitespace}{comment_char} {code} {comment_suffix}\n")
            else:
                commented_lines.append(f"{whitespace}{comment_char} {code}\n")

    if suffix_comment:
        commented_lines.append(f"{comment_char} {suffix_comment}\n")

    # Build new file
    result_lines = lines[:start_line - 1] + commented_lines + lines[end_line:]
    p.write_text("".join(result_lines))

    # Save to ledger: store the commented block string so we can find it later
    commented_block = "".join(commented_lines)
    original_block = "".join(lines[start_line - 1:end_line])

    ledger = _load_ledger()
    ledger.setdefault(file_path, []).append({
        "commented": commented_block,
        "original": original_block,
    })
    _save_ledger(ledger)

    actual_start = start_line
    actual_end = start_line + len(commented_lines) - 1
    return f"Commented {actual_start}-{actual_end}"


@mcp.tool()
def uncomment(
    file_path: str,
    start_line: int,
    end_line: int,
) -> str:
    """Uncomment previously commented-out lines in a file.

    Removes one layer of comment prefix from each line in the range.

    Args:
        file_path: Absolute path to the file.
        start_line: First line to uncomment (1-indexed).
        end_line: Last line to uncomment (1-indexed, inclusive).

    Returns:
        Summary of what was done.
    """
    p = Path(file_path)
    if not p.exists():
        return f"ERROR: File not found: {file_path}"

    content = p.read_text()
    lines = content.splitlines(keepends=True)
    total = len(lines)

    if start_line < 1 or end_line < 1:
        return "ERROR: Line numbers must be >= 1"
    if start_line > total or end_line > total:
        return f"ERROR: File has {total} lines, requested {start_line}-{end_line}"
    if start_line > end_line:
        return "ERROR: start_line must be <= end_line"

    # Check ledger for a matching commented block
    ledger = _load_ledger()
    entries = ledger.get(file_path, [])

    target_block = "".join(lines[start_line - 1:end_line])

    # Find matching entry in ledger
    match = None
    match_idx = None
    for idx, entry in enumerate(entries):
        if entry["commented"] == target_block:
            match = entry
            match_idx = idx
            break

    if match is None:
        return "ERROR: Cannot find this block in the comment ledger. This tool only uncomments comments it made. Remove manually instead."

    # Replace the commented block with the original
    original = match["original"]
    new_content = content.replace(target_block, original, 1)

    if new_content == content:
        # String replace failed somehow — restore and error
        return "ERROR: Could not remove cleanly. Block was in ledger but string match failed in file. Remove manually instead."

    # Verify the replacement is clean — only the target block should differ
    p.write_text(new_content)

    # Remove from ledger
    entries.pop(match_idx)
    if not entries:
        del ledger[file_path]
    else:
        ledger[file_path] = entries
    _save_ledger(ledger)

    original_lines = original.count("\n")
    return f"Uncommented {start_line}-{start_line + original_lines - 1}"


if __name__ == "__main__":
    mcp.run()
