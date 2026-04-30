"""Dragonbones hook entry point."""

import json
import logging
import os
import sys

LOG_FILE = "/tmp/dragonbones_v1_hook.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dragonbones")

# Suppress transitive import noise
os.environ["LITELLM_LOG"] = "ERROR"
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)

from dragonbones.constants import UNSILENCE_MARKER
from dragonbones.transcript import get_last_assistant_text
from dragonbones.parser import extract_from_blocks
from dragonbones.logs import persist_logs, validate_logs
from dragonbones.compiler import compile_concepts


def main():
    hook_input = json.load(sys.stdin)

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path or not os.path.exists(transcript_path):
        sys.exit(0)

    text, line_index, skill_calls, tools_called = get_last_assistant_text(transcript_path)
    if not text:
        sys.exit(0)

    session_id = os.path.basename(transcript_path).replace('.jsonl', '').replace('-', '_')

    unsilenced = UNSILENCE_MARKER in text
    silenced = not unsilenced
    short_response = len(text) < 100

    # Escape clause: response ending with ONLY 🔍 or 👍 = "I'm showing the user something
    # via tmux" or "I'm acknowledging a system command". Skip all validation.
    last_line = text.strip().split("\n")[-1].strip() if text.strip() else ""
    if last_line in ("🔍", "👍"):
        sys.exit(0)

    # Persist *Logs to CartON every turn
    if not short_response:
        try:
            persist_logs(text, session_id, line_index)
        except Exception:
            logger.exception("persist_logs failed")

    concepts, stubs, help_requested, blocks_found = extract_from_blocks(text)

    # Detect DB skill block for auto-log construction
    _has_db_skill = any(
        "Skill" in [t for r in c.get("relationships", [])
                     if r["relationship"] == "is_a" for t in r["related"]]
        for c in concepts
    )

    # No DB blocks — validate *logs only
    if blocks_found == 0:
        if not short_response:
            log_errors = validate_logs(text, skill_calls, tools_called, line_index)
            if log_errors:
                sys.stderr.write("\n".join(log_errors) + "\n")
                sys.exit(2)
        sys.exit(0)

    results = list(stubs)

    # Compile EntityChains
    compile_results, compiled_count, warning_count = compile_concepts(concepts, silenced)
    results.extend(compile_results)

    # Validate *logs
    log_errors = []
    if not short_response:
        log_errors = validate_logs(text, skill_calls, tools_called, line_index,
                                   has_db_skill_block=_has_db_skill,
                                   has_any_db_block=(blocks_found > 0))

    has_chains = bool(concepts) or bool(stubs)

    # SILENT MODE (default): compile quietly, show *log errors only
    # CartON compilation errors ALWAYS surface — never silenced
    if silenced and not help_requested:
        if compiled_count:
            logger.info("Silent compile: %d concepts", compiled_count)
        carton_errors = [r for r in compile_results if "ERROR" in r or "SOUP" in r or "BLOCKED" in r]
        all_errors = carton_errors + log_errors
        if all_errors:
            sys.stderr.write("\n".join(all_errors) + "\n")
            sys.exit(2)
        sys.exit(0)

    if not has_chains and not help_requested and not log_errors:
        sys.exit(0)

    # VERBOSE MODE (💭⛈️): full feedback
    stub_count = len(stubs) - (1 if help_requested else 0)
    parts = []
    if compiled_count:
        parts.append(f"{compiled_count} compiled")
    if warning_count:
        parts.append(f"⚠️ {warning_count} warning(s)")
    if stub_count > 0:
        parts.append(f"{stub_count} stub(s)")
    if help_requested:
        parts.append("help")
    if log_errors:
        parts.append(f"{len(log_errors)} log error(s)")

    if log_errors:
        results.extend(log_errors)

    summary = ", ".join(parts) if parts else f"0 chains in {blocks_found} block(s)"
    feedback = "\n".join(results) if results else "200 OK"
    sys.stderr.write(f"🐉🦴 Dragonbones [{summary}]:\n{feedback}\n")
    sys.exit(2)


if __name__ == "__main__":
    main()
