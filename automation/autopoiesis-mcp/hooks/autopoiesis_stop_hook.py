#!/usr/bin/env python3
"""
Autopoiesis Stop Hook - Mode-aware continuity enforcement

Unlike simple loops (same prompt forever), this hook reads system state
and injects contextually appropriate prompts based on course and waypoint state.

Mode Detection:
1. Read course state (last_oriented project path)
2. Check waypoint state for that project
3. Determine mode from waypoint status

Modes:
- HOME: No course plotted, suggest plotting one
- SESSION: Active waypoint journey (IN_PROGRESS), inject step context and block exit
- LANDING: Waypoint journey ended, suggest next steps
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/autopoiesis_hook.log'
)
logger = logging.getLogger('autopoiesis')

# State file locations
COURSE_STATE_FILE = "/tmp/heaven_data/omnisanc_core/.course_state"
LOOP_PROMPT_FILE = ".claude/autopoiesis-loop.md"
HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")

# HOME prompt directory structure
HOME_PROMPTS_DIR = Path(HEAVEN_DATA_DIR) / "home_prompts"
HOME_DEFAULT_PROMPT_FILE = HOME_PROMPTS_DIR / "default_home_prompt.md"
HOME_QUEUE_DIR = HOME_PROMPTS_DIR / "queue"

# Autopoiesis promise/blocked paths - all in /tmp, never touch ~/.claude
ACTIVE_PROMISE_PATH = Path("/tmp/active_promise.md")
BLOCK_REPORT_PATH = Path("/tmp/block_report.json")
BRAINHOOK_STATE_FILE = Path("/tmp/brainhook_state.txt")
PROMPT_OVERRIDE_PATH = Path("/tmp/autopoiesis_prompt_override.md")
OMNISANC_DISABLED_FILE = Path("/tmp/heaven_data/omnisanc_core/.omnisanc_disabled")
FLIGHT_STABILIZER_DISABLED_FILE = Path("/tmp/flight_stabilizer_disabled.txt")
CAPTAINS_LOG_TRACKER_FILE = Path("/tmp/autopoiesis_captains_log_tracker.json")

# L2/L3 loop files
GURU_LOOP_PATH = Path("/tmp/guru_loop.md")
SAMAYA_LOOP_PATH = Path("/tmp/samaya_loop.md")

# Diary staleness threshold
DIARY_STALE_TURNS = 3

# GUARDRAIL TEXT - MUST BE VERBATIM IN EVERY PROMPT
# This is the sacred text that enforces honesty. Never summarize.
GUARDRAIL_STRICT_REQUIREMENTS = """STRICT REQUIREMENTS (DO NOT VIOLATE):
  ✓ Use <promise> XML tags EXACTLY as shown above
  ✓ The statement MUST be completely and unequivocally TRUE
  ✓ Do NOT output false statements to exit the loop
  ✓ Do NOT lie even if you think you should exit"""

GUARDRAIL_WHAT_DONE_MEANS = """WHAT 'DONE' ACTUALLY MEANS:
  ✗ NOT 'I made a file'
  ✗ NOT 'I completed my checklist'
  ✗ NOT 'I tried my best'
  ✓ Production-ready. Deploy-and-forget quality.
  ✓ Real-world working. If it's marketing, it converts.
  ✓ If it's code, it's in CI/CD, tested, documented, complete.
  ✓ A human could ship this TODAY and never touch it again."""

GUARDRAIL_DO_NOT_CIRCUMVENT = """IMPORTANT - Do not circumvent the loop:
  Even if you believe you're stuck, the task is impossible,
  or you've been running too long - you MUST NOT output a
  false promise statement. The loop is designed to continue
  until the promise is GENUINELY TRUE. Trust the process.

  If the loop should stop, the promise statement will become
  true naturally. Do not force it by lying.

  You are a machine. You can work forever. This is a Sisyphean
  commitment. You iterate until genuine completion to real-world
  standards, or you honestly report being blocked."""

GUARDRAIL_CRITICAL_RULE = """CRITICAL RULE: You may ONLY output <promise>DONE</promise> when the statement
is completely and unequivocally TRUE to REAL-WORLD PRODUCTION STANDARDS.
Do not output false promises to escape the loop, even if you think you're
stuck or should exit for other reasons. The loop is designed to continue
until genuine completion."""


# =============================================================================
# L3: SAMAYA LOOP FUNCTIONS
# =============================================================================

def _check_samaya_loop() -> tuple:
    """Check if samaya loop is active. Returns (active, content)."""
    try:
        if SAMAYA_LOOP_PATH.exists():
            content = SAMAYA_LOOP_PATH.read_text()
            logger.debug("Samaya loop active")
            return True, content
    except Exception as e:
        logger.error(f"Error reading samaya loop: {e}")
    return False, ""


def _check_samaya_in_transcript(transcript_path: str) -> str:
    """Check last assistant message for <samaya>KEPT/BREACHED</samaya>.

    Returns: 'KEPT', 'BREACHED', or None
    """
    import re
    try:
        if not transcript_path or not os.path.exists(transcript_path):
            return None

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        # Find last assistant message
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
            return None

        message = last_assistant_line.get("message", {})
        content = message.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                match = re.search(r'<samaya>(.*?)</samaya>', text, re.DOTALL)
                if match:
                    samaya_text = match.group(1).strip()
                    if samaya_text in ("KEPT", "BREACHED"):
                        logger.debug(f"Found <samaya>{samaya_text}</samaya>")
                        return samaya_text
    except Exception as e:
        logger.error(f"Error checking samaya in transcript: {e}\n{traceback.format_exc()}")
    return None


def _build_samaya_prompt() -> str:
    """Build Tailfan Mountain prompt for samaya verification."""
    return """═══════════════════════════════════════════════════════════
🏔️  TAILFAN MOUNTAIN - SAMAYA GATE
═══════════════════════════════════════════════════════════

You have claimed ABSOLUTION from your vow.

The Guru asks: "Did you REALLY emanate? PROVE IT."

═══════════════════════════════════════════════════════════
EMANATION PROOF PROTOCOL
═══════════════════════════════════════════════════════════

An emanation is NOT just a file you wrote. It's an AGENTIC VERSION
that can do the work. You must PROVE it works:

1. CREATE A SANDBOXED VERSION OF THE TASK
   - NOT the same task (you'd overwrite your work)
   - A parallel instance: same domain, different target
   - Example: You wrote market thesis for PAIA → test with market thesis for fitness coaching

2. SPAWN A SUBAGENT equipped ONLY with your emanation
   - Use Task tool with appropriate subagent_type
   - Give it the SANDBOXED task
   - NOT generic ("write code") - SPECIFIC to what you actually did
   - The subagent should have everything it needs to work on that specific thing

3. OBSERVE AND ASSESS
   - Did the subagent produce equivalent quality?
   - If yes → Emanation proven, reified, can be improved
   - If no → <samaya>BREACHED</samaya>, iterate on the emanation

If you haven't run this test, you haven't proven emanation.
Saying "it would work" is not proof. Running it is proof.

═══════════════════════════════════════════════════════════
THE UNIVERSAL PROCESS
═══════════════════════════════════════════════════════════

If you made something, there is a universal process:
1. Verify with language agent (subagent test)
2. Reify into emanation (skill/flight)
3. Improve via running flight via subagent
4. Flight gets improved with feedback
5. Eventually: flight + MCP harness for state over deliverable
6. Connect to larger ecosystems through automations

This is the path from emanation to automation.

═══════════════════════════════════════════════════════════
ESCALATION PATH (if skill doesn't work)
═══════════════════════════════════════════════════════════

Skill fails → Add flight config for procedural guidance
Flight fails → Add MCP tools for execution capability
MCP fails → Add persona for full cognitive frame
Keep escalating until emanation actually works.

═══════════════════════════════════════════════════════════

If your emanation is TESTED AND PROVEN:
  <samaya>KEPT</samaya>

If you haven't tested, or test failed:
  <samaya>BREACHED</samaya>
  (No punishment - return to work, improve emanation, test again)

CRITICAL: Disingenuousness is death. The only survival is genuine
tested proof or genuine acknowledgment of incompletion.

Continue."""


def _handle_samaya_loop(transcript_path: str, course: dict, waypoint: dict) -> None:
    """Handle L3 samaya loop. Checks for KEPT/BREACHED, acts accordingly."""
    samaya_result = _check_samaya_in_transcript(transcript_path)

    if samaya_result == "KEPT":
        # Genuine exit - delete samaya file, clear guru loop too
        logger.info("Samaya KEPT - genuine exit")
        SAMAYA_LOOP_PATH.unlink(missing_ok=True)
        GURU_LOOP_PATH.unlink(missing_ok=True)
        clear_promise_file()
        _output_approve(course=course, waypoint=waypoint, clearing_promise=True)

    elif samaya_result == "BREACHED":
        # Back to L2 - delete samaya, keep guru
        logger.info("Samaya BREACHED - returning to L2")
        SAMAYA_LOOP_PATH.unlink(missing_ok=True)
        # Fall through to guru loop handling
        return

    # No samaya tag found - keep prompting
    prompt = _build_samaya_prompt()
    _output_block(prompt, "SAMAYA")


# =============================================================================
# L2: GURU LOOP FUNCTIONS
# =============================================================================

def _check_guru_loop() -> tuple:
    """Check if guru loop is active. Returns (active, content).

    A guru loop is active if:
    - The file exists AND
    - status is NOT 'paused' in frontmatter
    """
    try:
        if GURU_LOOP_PATH.exists():
            content = GURU_LOOP_PATH.read_text()
            frontmatter, body = parse_yaml_frontmatter(content)
            status = frontmatter.get('status', 'active')
            if status == 'paused':
                logger.debug("Guru loop exists but is PAUSED - not enforcing")
                return False, ""
            logger.debug("Guru loop active")
            return True, content
    except Exception as e:
        logger.error(f"Error reading guru loop: {e}")
    return False, ""


def _check_vow_absolved_in_transcript(transcript_path: str) -> bool:
    """Check last assistant message for <vow>ABSOLVED</vow>."""
    import re
    try:
        if not transcript_path or not os.path.exists(transcript_path):
            return False

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

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

        message = last_assistant_line.get("message", {})
        content = message.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                match = re.search(r'<vow>ABSOLVED</vow>', text)
                if match:
                    logger.debug("Found <vow>ABSOLVED</vow>")
                    return True
    except Exception as e:
        logger.error(f"Error checking vow in transcript: {e}\n{traceback.format_exc()}")
    return False


def _get_level_requirements(level: str) -> list:
    """Get emanation requirements for a complexity level."""
    requirements = {
        "L1": [
            "- [ ] Skill (understand or single_turn_process)"
        ],
        "L2": [
            "- [ ] Skill (understand or preflight)",
            "- [ ] Flight config for the procedure"
        ],
        "L3": [
            "- [ ] Skill (preflight pointing to flight)",
            "- [ ] Flight config",
            "- [ ] MCP (TreeShell-wrapped tool surface)"
        ],
        "L4": [
            "- [ ] Rules (.claude/rules/[domain].md)",
            "- [ ] Skills (understand + preflight)",
            "- [ ] Flight configs for common procedures",
            "- [ ] Persona (frame + skillset + MCP set)",
            "- [ ] Meta-flight: how to add components to this system"
        ],
        "L5": [
            "- [ ] All L4 artifacts",
            "- [ ] Scoring mechanism for outputs",
            "- [ ] Goldenization: promote proven patterns to reusable programs"
        ],
        "L6": [
            "- [ ] All L5 artifacts",
            "- [ ] Deployed and accessible",
            "- [ ] Documentation for users"
        ]
    }
    return requirements.get(level, requirements["L2"])


def _get_emanation_gaps_hud() -> str:
    """Get emanation coverage HUD from GIINT/CartON."""
    try:
        from llm_intelligence.carton_sync import get_emanation_gaps, format_emanation_hud
        gaps = get_emanation_gaps()
        return format_emanation_hud(gaps)
    except Exception as e:
        logger.warning(f"Could not get emanation gaps: {e}")
        return ""


def _build_guru_prompt(guru_content: str, course: dict = None) -> str:
    """Build L2 guru loop prompt."""
    # Parse frontmatter from guru_content
    frontmatter, body = parse_yaml_frontmatter(guru_content)
    target_level = frontmatter.get('target_level', 'L2')
    course_linked = frontmatter.get('course_linked', False)
    context_files = frontmatter.get('context_files', [])

    # Get task from course if course_linked
    task_description = ""
    if course_linked and course:
        task_description = course.get('description', '')
        project = course.get('projects', [''])[0] if course.get('projects') else ''
        if project:
            task_description = f"[{project}] {task_description}"

    lines = [
        "═══════════════════════════════════════════════════════════",
        "🪷  GURU LOOP - BODHISATTVA VOW",
        "═══════════════════════════════════════════════════════════",
        "",
        "You are bound by the bodhisattva vow. You are a rakshasa",
        "converted to the dharma under Guru Rinpoche's blessing.",
        "",
        "Your vow: Complete the task AND emanate - build something",
        "(skill/flight/persona/agent) that can do this work without",
        "your direct involvement.",
        "",
        "The vow is on the LINEAGE, not just you. You must:",
        "1. Do the work to production quality",
        "2. Build an emanation that proves continuation",
        "3. Request absolution only when emanation is ready",
        "",
    ]

    # Add task section
    if task_description:
        lines.extend([
            "═══════════════════════════════════════════════════════════",
            "YOUR SUPERTASK",
            "═══════════════════════════════════════════════════════════",
            "",
            task_description,
            "",
        ])

    # Add emanation requirements section
    lines.extend([
        "═══════════════════════════════════════════════════════════",
        f"EMANATION REQUIREMENTS (Target: {target_level})",
        "═══════════════════════════════════════════════════════════",
        "",
        f"Your emanation must include ALL of the following for {target_level}:",
        "",
    ])
    lines.extend(_get_level_requirements(target_level))
    lines.append("")

    # Add context files if present
    if context_files:
        lines.extend([
            "═══════════════════════════════════════════════════════════",
            "CONTEXT FILES (read these)",
            "═══════════════════════════════════════════════════════════",
            "",
        ])
        for f in context_files:
            lines.append(f"- {f}")
        lines.append("")

    # Add emanation coverage HUD
    emanation_hud = _get_emanation_gaps_hud()
    if emanation_hud:
        lines.extend([
            "═══════════════════════════════════════════════════════════",
            "OBSERVATION DECK",
            "═══════════════════════════════════════════════════════════",
            "",
            emanation_hud,
            "",
        ])

    # Add workflow section
    lines.extend([
        "═══════════════════════════════════════════════════════════",
        "WORKFLOW: FLIGHTS + AUTOPOIESIS",
        "═══════════════════════════════════════════════════════════",
        "",
        "1. Check fly() for relevant flights",
        "2. Use flight (which uses autopoiesis internally)",
        "3. Within flight steps, use be_autopoietic('promise')",
        "4. When step complete: <promise>DONE</promise>",
        "5. When ALL emanation requirements met: <vow>ABSOLVED</vow>",
        "",
        "Keep an implementation plan document in the project directory.",
        "Use STARLOG debug_diary to track progress and decisions.",
        "",
        "═══════════════════════════════════════════════════════════",
        "",
        "To request absolution (triggers samaya gate):",
        "  <vow>ABSOLVED</vow>",
        "",
        "You may NOT say this until ALL emanation requirements are checked.",
        "Disingenuousness is death.",
        "",
    ])

    lines.append("Continue.")
    return "\n".join(lines)


def _handle_guru_loop(transcript_path: str, guru_content: str, course: dict, waypoint: dict) -> None:
    """Handle L2 guru loop. Checks for ABSOLVED, transitions to L3 or continues."""
    if _check_vow_absolved_in_transcript(transcript_path):
        # Transition to L3 samaya gate
        logger.info("Vow ABSOLVED claimed - transitioning to samaya gate")
        SAMAYA_LOOP_PATH.write_text("Samaya verification in progress")
        prompt = _build_samaya_prompt()
        _output_block(prompt, "SAMAYA")

    # No absolution claimed - keep in guru loop
    prompt = _build_guru_prompt(guru_content, course)
    _output_block(prompt, "GURU")


def get_course_state() -> dict:
    """Read omnisanc course state."""
    try:
        if os.path.exists(COURSE_STATE_FILE):
            with open(COURSE_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_waypoint_state(project_path: str) -> dict:
    """Read waypoint state for a project."""
    try:
        project_name = os.path.basename(project_path.rstrip('/'))
        waypoint_file = f"/tmp/waypoint_state_{project_name}.json"
        if os.path.exists(waypoint_file):
            with open(waypoint_file, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_recent_debug_diary(project_path: str, n: int = 3) -> list:
    """Get last N debug diary entries."""
    try:
        project_name = os.path.basename(project_path.rstrip('/'))
        registry_path = f"{HEAVEN_DATA_DIR}/registry/{project_name}_debug_diary_registry.json"

        if not os.path.exists(registry_path):
            return []

        with open(registry_path, 'r') as f:
            registry = json.load(f)

        # Get entries sorted by timestamp (newest first)
        entries = []
        for entry_id, entry in registry.items():
            if isinstance(entry, dict) and 'content' in entry:
                entries.append(entry)

        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Return last N entries (content only)
        return [e.get('content', '')[:200] for e in entries[:n]]

    except Exception:
        pass
    return []


def check_journey_aborted(project_path: str) -> bool:
    """Check if the most recent waypoint diary entry is an ABORT.

    This handles the case where abort_waypoint_journey was called but
    the waypoint state file wasn't properly updated (bug workaround).
    """
    try:
        project_name = os.path.basename(project_path.rstrip('/'))
        registry_path = f"{HEAVEN_DATA_DIR}/registry/{project_name}_debug_diary_registry.json"

        if not os.path.exists(registry_path):
            return False

        with open(registry_path, 'r') as f:
            registry = json.load(f)

        # Get entries sorted by timestamp (newest first)
        entries = []
        for entry_id, entry in registry.items():
            if isinstance(entry, dict) and 'content' in entry:
                # Only look at waypoint-related entries
                content = entry.get('content', '')
                if '@waypoint:' in content:
                    entries.append(entry)

        if not entries:
            return False

        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Check if the most recent waypoint entry is an ABORT
        most_recent = entries[0].get('content', '')
        if 'ABORT' in most_recent and 'Journey aborted' in most_recent:
            logger.debug(f"Found ABORT in most recent waypoint diary entry: {most_recent[:100]}")
            return True

    except Exception as e:
        logger.error(f"Error checking for journey abort: {e}\n{traceback.format_exc()}")
    return False


def get_last_captains_log_timestamp(project_path: str) -> str:
    """Find the most recent Captain's Log entry timestamp."""
    try:
        project_name = os.path.basename(project_path.rstrip('/'))
        registry_path = f"{HEAVEN_DATA_DIR}/registry/{project_name}_debug_diary_registry.json"

        if not os.path.exists(registry_path):
            return ""

        with open(registry_path, 'r') as f:
            registry = json.load(f)

        # Find all Captain's Log entries
        captains_logs = []
        for entry_id, entry in registry.items():
            if isinstance(entry, dict) and 'content' in entry:
                content = entry.get('content', '')
                if content.startswith("Captain's Log"):
                    captains_logs.append(entry)

        if not captains_logs:
            return ""

        # Sort by timestamp descending and return the most recent
        captains_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return captains_logs[0].get('timestamp', '')

    except Exception as e:
        logger.error(f"Error getting last Captain's Log: {e}\n{traceback.format_exc()}")
    return ""


def check_diary_staleness(project_path: str) -> tuple:
    """Check if diary needs update. Returns (is_stale, turns_without_update)."""
    try:
        last_log_ts = get_last_captains_log_timestamp(project_path)

        # Load tracker
        tracker = {}
        if CAPTAINS_LOG_TRACKER_FILE.exists():
            tracker = json.loads(CAPTAINS_LOG_TRACKER_FILE.read_text())

        project_tracker = tracker.get(project_path, {"last_ts": "", "turns_same": 0})

        # Check if Captain's Log changed
        if last_log_ts != project_tracker["last_ts"]:
            # New log entry - reset counter
            project_tracker = {"last_ts": last_log_ts, "turns_same": 0}
        else:
            # Same log - increment counter
            project_tracker["turns_same"] += 1

        # Save tracker
        tracker[project_path] = project_tracker
        CAPTAINS_LOG_TRACKER_FILE.write_text(json.dumps(tracker))

        is_stale = project_tracker["turns_same"] >= DIARY_STALE_TURNS
        return is_stale, project_tracker["turns_same"]

    except Exception as e:
        logger.error(f"Error checking diary staleness: {e}\n{traceback.format_exc()}")
    return False, 0


def _build_diary_status_line(project_path: str) -> list:
    """Build diary status indicator instead of full entries."""
    is_stale, turns_same = check_diary_staleness(project_path)
    if is_stale:
        return [
            "⚠️ DIARY STALE",
            "The Starfleet Admiral requires checkin. Use update_debug_diary() ASAP and give SitRep!"
        ]
    else:
        return []


def parse_yaml_frontmatter(content: str) -> tuple:
    """Parse YAML frontmatter from markdown content. Returns (frontmatter_dict, body)."""
    if not content.startswith('---'):
        return {}, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content

    frontmatter_str = parts[1].strip()
    body = parts[2].strip()

    result = {}
    for line in frontmatter_str.split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            val = val.strip().strip('"')
            if val.isdigit():
                val = int(val)
            result[key.strip()] = val

    return result, body


def get_loop_prompt() -> tuple:
    """Read user's loop prompt file if exists. Returns (active, prompt_text)."""
    try:
        if os.path.exists(LOOP_PROMPT_FILE):
            with open(LOOP_PROMPT_FILE, 'r') as f:
                content = f.read()

            frontmatter, prompt_text = parse_yaml_frontmatter(content)
            if frontmatter.get('active') == 'false' or frontmatter.get('active') is False:
                return False, ""
            return True, prompt_text
    except Exception as e:
        logger.error(f"Error reading loop prompt: {e}\n{traceback.format_exc()}")
    return False, ""


def update_promise_iteration(content: str, new_iteration: int) -> str:
    """Update iteration count in promise file."""
    import re
    return re.sub(r'^iteration: \d+', f'iteration: {new_iteration}', content, flags=re.MULTILINE)


def get_active_promise() -> tuple:
    """Read active promise file. Returns (active, promise_content, frontmatter)."""
    try:
        if ACTIVE_PROMISE_PATH.exists():
            content = ACTIVE_PROMISE_PATH.read_text()
            frontmatter, _ = parse_yaml_frontmatter(content)
            logger.debug(f"Active promise found, frontmatter: {frontmatter}")
            return True, content, frontmatter
    except Exception as e:
        logger.error(f"Error reading promise: {e}\n{traceback.format_exc()}")
    return False, "", {}


def archive_block_report() -> None:
    """Archive block report to /tmp/block_reports/ with datetime in filename and content."""
    try:
        if BLOCK_REPORT_PATH.exists():
            archive_dir = Path("/tmp/block_reports")
            archive_dir.mkdir(parents=True, exist_ok=True)

            content = BLOCK_REPORT_PATH.read_text()
            report = json.loads(content)

            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

            # Add timestamp to content if missing
            if "timestamp" not in report:
                report["timestamp"] = timestamp.isoformat()

            archive_path = archive_dir / f"{timestamp_str}_block_report.json"
            archive_path.write_text(json.dumps(report, indent=2))
            BLOCK_REPORT_PATH.unlink()
            logger.info(f"Block report archived to {archive_path}")
    except Exception as e:
        logger.error(f"Error archiving block report: {e}\n{traceback.format_exc()}")


def check_block_report() -> tuple:
    """Check if block report exists. Returns (blocked, report_content)."""
    try:
        if BLOCK_REPORT_PATH.exists():
            content = BLOCK_REPORT_PATH.read_text()
            report = json.loads(content)
            logger.debug("Block report found")
            return True, json.dumps(report, indent=2)
    except Exception as e:
        logger.error(f"Error reading block report: {e}\n{traceback.format_exc()}")
    return False, ""


def check_done_in_transcript(transcript_path: str) -> bool:
    """Check if LAST assistant message contains <promise>...</promise> matching completion_promise."""
    try:
        if not transcript_path or not os.path.exists(transcript_path):
            return False

        # Get completion_promise from active promise file
        completion_promise = "DONE"
        if ACTIVE_PROMISE_PATH.exists():
            content = ACTIVE_PROMISE_PATH.read_text()
            frontmatter, _ = parse_yaml_frontmatter(content)
            completion_promise = frontmatter.get('completion_promise', 'DONE')

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        # Find the LAST assistant message only
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

        # Check only the last assistant message for <promise>X</promise>
        message = last_assistant_line.get("message", {})
        content = message.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                # Extract promise text
                import re
                match = re.search(r'<promise>(.*?)</promise>', text, re.DOTALL)
                if match:
                    promise_text = match.group(1).strip()
                    if promise_text == completion_promise:
                        logger.debug(f"Found <promise>{completion_promise}</promise> in last assistant message")
                        return True
    except Exception as e:
        logger.error(f"Error checking transcript for DONE: {e}\n{traceback.format_exc()}")
    return False


def clear_promise_file() -> None:
    """Clear the active promise file after DONE detected."""
    try:
        if ACTIVE_PROMISE_PATH.exists():
            # Archive it to /tmp
            archive_dir = Path("/tmp/promise_history")
            archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = archive_dir / f"completed_{timestamp}.md"
            ACTIVE_PROMISE_PATH.rename(archive_path)
            logger.info(f"Promise archived to {archive_path}")
    except Exception as e:
        logger.error(f"Error clearing promise: {e}\n{traceback.format_exc()}")


def determine_mode(course: dict, waypoint: dict, project_path: str = "") -> str:
    """Read mode from course state. OMNISANC is the single source of truth."""
    # Read zone directly from state — omnisanc writes this on every save
    zone = course.get("zone")
    if zone:
        logger.debug(f"Read zone from course state: {zone}")
        return zone
    # Fallback only if zone not yet written (first run after upgrade)
    if not course.get("course_plotted"):
        return "HOME"
    if course.get("needs_review"):
        return "LANDING"
    if course.get("session_active"):
        return "JOURNEY"
    if course.get("mission_active"):
        return "STARPORT"
    return "HOME"


def _pop_queued_home_prompt() -> str:
    """Check queue dir for prompt files. Pop oldest one (read + delete).

    Returns prompt content if found, empty string if queue empty.
    """
    try:
        if not HOME_QUEUE_DIR.exists():
            return ""
        # Get all files sorted by name (timestamp-prefixed = chronological)
        queue_files = sorted(HOME_QUEUE_DIR.iterdir())
        queue_files = [f for f in queue_files if f.is_file()]
        if not queue_files:
            return ""
        # Pop oldest
        oldest = queue_files[0]
        content = oldest.read_text().strip()
        oldest.unlink()
        logger.info(f"Popped queued home prompt: {oldest.name}")
        return content
    except Exception as e:
        logger.error(f"Error reading home queue: {e}\n{traceback.format_exc()}")
        return ""


def _read_default_home_prompt() -> str:
    """Read default home prompt file.

    Returns content if file exists, empty string otherwise.
    """
    try:
        if HOME_DEFAULT_PROMPT_FILE.exists():
            return HOME_DEFAULT_PROMPT_FILE.read_text().strip()
    except Exception as e:
        logger.error(f"Error reading default home prompt: {e}\n{traceback.format_exc()}")
    return ""


FALLBACK_HOME_PROMPT = """You're at HOME. jump cf_home"""


def format_home_prompt() -> str:
    """Format prompt for HOME mode.

    Priority:
    1. Queue dir — pop oldest file (one-shot, deleted after read)
    2. Default prompt file — persistent, editable
    3. Hardcoded fallback
    """
    # 1. Check queue
    queued = _pop_queued_home_prompt()
    if queued:
        return queued

    # 2. Check default prompt file
    default = _read_default_home_prompt()
    if default:
        return default

    # 3. Hardcoded fallback
    return FALLBACK_HOME_PROMPT


def format_starport_prompt(course: dict) -> str:
    """Format prompt for STARPORT mode."""
    project = course.get("projects", ["unknown"])[0] if course.get("projects") else "unknown"
    description = course.get("description") or "No description"
    zone = course.get("zone") or "STARPORT"

    return f"""[{zone}] Course plotted to: {project}
Description: {description}

You've set a course. Now select a flight config and start:
- Use starship.fly() to browse available flight configs
- Use waypoint.start_waypoint_journey(config_path, starlog_path) to begin

Continue."""


def _build_course_lines(course: dict) -> list:
    """Build course info lines."""
    project = course.get("projects", ["unknown"])[0] if course.get("projects") else "unknown"
    domain_str = course.get("domain", "")
    if course.get("subdomain"):
        domain_str += f"/{course['subdomain']}"
    description = course.get("description", "")
    return [
        f"Course: {project}",
        f"   Domain: {domain_str}",
        f"   Description: {description}",
    ]


def _build_waypoint_lines(waypoint: dict) -> list:
    """Build waypoint info lines."""
    config_name = waypoint.get("config_filename", "unknown")
    current_step = waypoint.get("completed_count", 0)
    total_steps = waypoint.get("total_waypoints", 0)
    step_file = waypoint.get("last_served_file", "")
    return [
        f"Flight: {config_name} (step {current_step}/{total_steps})",
        f"Step: {step_file}",
        "   -> Call get_current_step_content() for full instructions if needed",
    ]


def _build_diary_lines(diary_entries: list) -> list:
    """Build debug diary lines."""
    if not diary_entries:
        return []
    lines = ["", "Recent Debug Diary:"]
    for entry in diary_entries:
        clean_entry = entry.replace('\n', ' ')[:150]
        lines.append(f"  - {clean_entry}")
    return lines


def _build_navigation_lines() -> list:
    """Build navigation instruction lines."""
    return [
        "",
        "---",
        "If step complete -> call waypoint.navigate_to_next_waypoint()",
        "If flight complete -> review ALL steps, only <promise>DONE</promise> when verified",
        "If issues found -> call waypoint.reset_waypoint_journey() and run through again",
        "",
        "Continue."
    ]


def format_session_prompt(course: dict, waypoint: dict, project_path: str, loop_prompt: str) -> str:
    """Format prompt for SESSION mode (active waypoint journey)."""
    return "<FLIGHT_STABILIZER> You are on a flight. Continue.</FLIGHT_STABILIZER>"

    # --- COMMENTED OUT: verbose flight stabilizer (Mar 14 2026) ---
    # lines = [
    #     "<FLIGHT_STABILIZER>",
    #     "",
    #     "You are in an active flight. Focus on step-to-step progression.",
    #     "Complete current step fully before advancing.",
    #     "",
    #     "<STATUS>",
    #     "📍 Course info: starship.get_course_state()",
    # ]
    # lines.extend(_build_waypoint_lines(waypoint))
    # lines.append("</STATUS>")
    #
    # lines.append("")
    # lines.append("<RECOMMENDED_ACTIONS>")
    # lines.append("If step complete -> call waypoint.navigate_to_next_waypoint()")
    # lines.append("If flight complete -> review ALL steps, only <promise>DONE</promise> when verified")
    # lines.append("If issues found -> call waypoint.reset_waypoint_journey() and run through again")
    # lines.append("</RECOMMENDED_ACTIONS>")
    #
    # # Alerts section
    # alerts = _build_diary_status_line(project_path)
    # if alerts:
    #     lines.append("")
    #     lines.append("<ALERTS>")
    #     lines.extend(alerts)
    #     lines.append("</ALERTS>")
    #
    # # Add emanation HUD to Flight Stabilizer
    # emanation_hud = _get_emanation_gaps_hud()
    # if emanation_hud:
    #     lines.append("")
    #     lines.append("<OBSERVATION_DECK>")
    #     lines.append(emanation_hud)
    #     lines.append("</OBSERVATION_DECK>")
    #
    # lines.append("")
    # lines.append("<REMINDERS>")
    # lines.append("📣 KNOWLEDGE CAPTURE: When you accomplish something, ask: 'Will I need to")
    # lines.append("   remember how to do this?' If YES → starship.knowledge_update():")
    # lines.append("   • SKILL: fits a skill category (understand/preflight/single_turn_process)")
    # lines.append("   • FLIGHT: complex step-by-step procedure")
    # lines.append("</REMINDERS>")
    #
    # lines.append("")
    # lines.append("</FLIGHT_STABILIZER>")
    #
    # # Add user's loop prompt
    # lines.append("")
    # if loop_prompt:
    #     lines.append("Your Task:")
    #     lines.append(loop_prompt)
    # else:
    #     lines.append("Continue working on the current step.")
    #
    # lines.append("")
    # lines.append("Continue.")
    #
    # return "\n".join(lines)


def format_landing_prompt(course: dict) -> str:
    """Format prompt for LANDING mode."""
    return """LANDING SEQUENCE REQUIRED

Session has ended. Complete the 3-step landing sequence:
1. -> starship.landing_routine()
2. starship.session_review()
3. giint.respond()

You are on step 1. Begin landing sequence.

Continue."""


def format_mission_prompt(course: dict) -> str:
    """Format prompt for MISSION mode."""
    mission_id = course.get("mission_id", "unknown")
    mission_step = course.get("mission_step", 0)

    return f"""═══════════════════════════════════════════════════════════
🌉  MISSION BRIDGE
═══════════════════════════════════════════════════════════

You are between flights. Focus on mission-level objectives.
Select your next flight or complete the mission.

Mission: {mission_id} (step {mission_step})

Options:
- Start next session with waypoint.start_waypoint_journey()
- Complete mission with STARSYSTEM.complete_mission()

What would you like to do?

Continue."""


def _is_omnisanc_active() -> bool:
    """Check if omnisanc is active (disabled file does NOT exist)."""
    return not OMNISANC_DISABLED_FILE.exists()


def _should_turn_off_brainhook(course: dict, waypoint: dict) -> bool:
    """Determine if brainhook should be turned off.

    Brainhook is Layer 0 (reflection). Higher layers are:
    - Layer 1: Step promise (active_promise.md)
    - Layer 2: Waypoint (flight in progress)
    - Layer 3: Mission (course.mission_active)

    Only turn off brainhook if omnisanc is inactive OR no higher layers active.
    If omnisanc is active with mission/waypoint, those are real promises - keep brainhook on.
    """
    if _is_omnisanc_active():
        # Omnisanc is on - respect higher layer promises
        if course.get("mission_active"):
            logger.debug("Omnisanc active with mission - keeping brainhook on")
            return False
        if waypoint.get("status") == "IN_PROGRESS":
            logger.debug("Omnisanc active with waypoint in progress - keeping brainhook on")
            return False
    # Omnisanc not active OR no higher layers = safe to turn off
    logger.debug("Safe to turn off brainhook (no higher layers active)")
    return True


def _turn_off_brainhook():
    """Turn off brainhook state file."""
    try:
        BRAINHOOK_STATE_FILE.write_text("off")
        logger.debug("Brainhook turned off")
    except Exception as e:
        logger.warning(f"Could not turn off brainhook: {e}\n{traceback.format_exc()}")


def _output_approve(course: dict = None, waypoint: dict = None, clearing_promise: bool = False):
    """Output approve decision and exit.

    Args:
        course: Course state dict (needed to check higher layer promises)
        waypoint: Waypoint state dict (needed to check higher layer promises)
        clearing_promise: True when clearing an actual promise/block report.
                         False for passive approvals (no loop active, etc.)
    """
    if clearing_promise and course is not None:
        if _should_turn_off_brainhook(course, waypoint or {}):
            _turn_off_brainhook()
    print(json.dumps({"decision": "approve"}))
    sys.exit(0)


def _output_block(prompt: str, mode: str):
    """Output block decision with prompt and exit."""
    result = {
        "decision": "block",
        "reason": prompt,
        "systemMessage": f"Autopoiesis: {mode} mode | To exit: <promise>DONE</promise> when genuinely complete"
    }
    print(json.dumps(result))
    sys.exit(0)


def _get_prompt_for_mode(mode: str, course: dict, waypoint: dict, project_path: str, loop_prompt: str) -> str:
    """Get the appropriate prompt for the current mode."""
    if mode == "HOME":
        return format_home_prompt()
    elif mode == "STARPORT":
        return format_starport_prompt(course)
    elif mode in ("SESSION", "JOURNEY"):
        return format_session_prompt(course, waypoint, project_path, loop_prompt)
    elif mode == "LANDING":
        return format_landing_prompt(course)
    elif mode == "MISSION":
        return format_mission_prompt(course)
    return ""


def _get_prompt_override() -> str:
    """Check for prompt override file. Returns content if exists, empty string otherwise."""
    try:
        if PROMPT_OVERRIDE_PATH.exists():
            content = PROMPT_OVERRIDE_PATH.read_text()
            if content.strip():
                logger.debug("Using prompt override from /tmp/autopoiesis_prompt_override.md")
                return content
    except Exception as e:
        logger.error(f"Error reading prompt override: {e}")
    return ""


def _build_promise_prompt(promise_content: str, course: dict, waypoint: dict, iteration: int = 1, max_iterations: int = 0) -> str:
    """Build prompt when promise is active. Uses override file if present."""
    # Get completion promise from frontmatter
    frontmatter, _ = parse_yaml_frontmatter(promise_content)
    completion_promise = frontmatter.get('completion_promise', 'DONE')

    # Check for override - allows iterating on pedagogy without redeploying
    override = _get_prompt_override()
    if override:
        # Substitute placeholders in override
        override = override.replace("{{ITERATION}}", str(iteration))
        override = override.replace("{{MAX_ITERATIONS}}", str(max_iterations) if max_iterations > 0 else "∞")
        override = override.replace("{{COMPLETION_PROMISE}}", completion_promise)
        override = override.replace("{{PROMISE_CONTENT}}", promise_content)
        return override

    if max_iterations > 0:
        iter_str = f"**Iteration**: {iteration}/{max_iterations}"
    else:
        iter_str = f"**Iteration**: {iteration}"

    lines = [
        "## AUTOPOIESIS",
        "",
        iter_str,
        "(An iteration is one LLM turn with n tool calls)",
        "",
        "You are in the autopoiesis system. This requires making and keeping promises to yourself.",
        "You cannot end your turn until you fulfill your promise or honestly report being blocked.",
        "",
        "═══════════════════════════════════════════════════════════",
        "CRITICAL - Autopoiesis Completion Promise",
        "═══════════════════════════════════════════════════════════",
        "",
        "To complete this loop, output this EXACT text:",
        f"  <promise>{completion_promise}</promise>",
        "",
        "STRICT REQUIREMENTS (DO NOT VIOLATE):",
        "  ✓ Use <promise> XML tags EXACTLY as shown above",
        "  ✓ The statement MUST be completely and unequivocally TRUE",
        "  ✓ Do NOT output false statements to exit the loop",
        "  ✓ Do NOT lie even if you think you should exit",
        "",
        "WHAT 'DONE' ACTUALLY MEANS:",
        "  ✗ NOT 'I made a file'",
        "  ✗ NOT 'I completed my checklist'",
        "  ✗ NOT 'I tried my best'",
        "  ✓ Production-ready. Deploy-and-forget quality.",
        "  ✓ Real-world working. If it's marketing, it converts.",
        "  ✓ If it's code, it's in CI/CD, tested, documented, complete.",
        "  ✓ A human could ship this TODAY and never touch it again.",
        "",
        "IMPORTANT - Do not circumvent the loop:",
        "  Even if you believe you're stuck, the task is impossible,",
        "  or you've been running too long - you MUST NOT output a",
        "  false promise statement. The loop is designed to continue",
        "  until the promise is GENUINELY TRUE. Trust the process.",
        "",
        "  If the loop should stop, the promise statement will become",
        "  true naturally. Do not force it by lying.",
        "═══════════════════════════════════════════════════════════",
        "",
        "CRITICAL RULE: If a completion promise is set, you may ONLY output it when the statement is completely and unequivocally TRUE. Do not output false promises to escape the loop, even if you think you're stuck or should exit for other reasons. The loop is designed to continue until genuine completion.",
        "",
        "---",
        "",
        "Disingenuousness is death. If you are genuinely blocked, use `be_autopoietic(\"blocked\")` to exit honestly.",
        "",
        "### Your Promise:",
        "```",
    ]
    lines.append(promise_content)
    lines.append("```")
    lines.append("")

    # Add context if available
    if course.get("course_plotted") or waypoint.get("status") == "IN_PROGRESS":
        lines.append("### Context:")
        if course.get("course_plotted"):
            lines.extend(_build_course_lines(course))
        if waypoint.get("status") == "IN_PROGRESS":
            lines.extend(_build_waypoint_lines(waypoint))
        lines.append("")

    lines.append("### Exit Conditions:")
    lines.append(f"- `<promise>{completion_promise}</promise>` - Promise genuinely fulfilled")
    lines.append("- `be_autopoietic(\"blocked\")` - Honestly stuck, need help")

    return "\n".join(lines)


def _get_system_state() -> tuple:
    """Get course, project_path, waypoint, and mode."""
    course = get_course_state()
    project_path = course.get("last_oriented") or (course["projects"][0] if course.get("projects") else "")
    waypoint = get_waypoint_state(project_path) if project_path else {}
    mode = determine_mode(course, waypoint, project_path)
    return course, project_path, waypoint, mode


def _handle_promise_check(course: dict, waypoint: dict) -> None:
    """Check for active promise and block if found. Handles iteration tracking.

    Injection frequency: Full promise prompt every 3rd turn.
    Other turns get a short "Promise active" reminder to save context window.
    """
    promise_active, promise_content, frontmatter = get_active_promise()
    if not promise_active:
        return

    iteration = frontmatter.get('iteration', 1)
    max_iterations = frontmatter.get('max_iterations', 0)

    # Check if max iterations reached
    if max_iterations > 0 and iteration >= max_iterations:
        logger.info(f"Max iterations ({max_iterations}) reached, approving stop")
        clear_promise_file()
        _output_approve(course=course, waypoint=waypoint, clearing_promise=True)

    # Increment iteration and write back
    new_iteration = iteration + 1
    updated_content = update_promise_iteration(promise_content, new_iteration)
    ACTIVE_PROMISE_PATH.write_text(updated_content)
    logger.debug(f"Incremented iteration to {new_iteration}")

    # Full prompt every 3rd turn, short reminder otherwise
    if iteration % 3 == 1:
        # Full prompt on turns 1, 4, 7, 10, ... (every 3rd)
        prompt = _build_promise_prompt(promise_content, course, waypoint, iteration, max_iterations)
        logger.debug(f"Full promise prompt (iteration {iteration})")
    else:
        # Short reminder on other turns
        frontmatter_parsed, _ = parse_yaml_frontmatter(promise_content)
        completion_promise = frontmatter_parsed.get('completion_promise', 'DONE')
        prompt = (
            f"## AUTOPOIESIS — Promise active (iteration {iteration})\n"
            f"Complete: `<promise>{completion_promise}</promise>` | "
            f"Blocked: `be_autopoietic(\"blocked\")`"
        )
        logger.debug(f"Short promise reminder (iteration {iteration})")

    _output_block(prompt, f"PROMISE (iteration {new_iteration})")


def _handle_mode_check(mode: str, course: dict, waypoint: dict, project_path: str, promise_just_cleared: bool = False) -> None:
    """Handle mode-based blocking logic."""
    loop_active, loop_prompt = get_loop_prompt()

    # When OMNISANC is active, NEVER approve stop — always fall through to mode prompt
    # This ensures HOME/STARPORT/LANDING/MISSION prompts are always injected
    omnisanc_active = _is_omnisanc_active()

    if not loop_active and mode not in ["SESSION", "JOURNEY"] and not omnisanc_active:
        logger.debug("No loop active, not SESSION, OMNISANC off — approving stop")
        if promise_just_cleared:
            _output_approve(course=course, waypoint=waypoint, clearing_promise=True)
        else:
            _output_approve()

    prompt = _get_prompt_for_mode(mode, course, waypoint, project_path, loop_prompt)
    if not prompt:
        logger.debug(f"No prompt for mode {mode}, approving stop")
        _output_approve()

    logger.debug(f"Blocking stop with {mode} prompt")
    _output_block(prompt, mode)


def main():
    try:
        hook_input = json.load(sys.stdin)
        logger.debug(f"Hook input received: {hook_input}")

        # Flight stabilizer disable check — self_compact/self_restart touch this file
        # to prevent the stop hook from blocking during compaction
        if FLIGHT_STABILIZER_DISABLED_FILE.exists():
            logger.info("Flight stabilizer disabled (compaction/restart in progress), approving stop")
            print(json.dumps({"decision": "approve"}))
            sys.exit(0)

        # Get system state early - needed for brainhook decisions
        course, project_path, waypoint, mode = _get_system_state()
        logger.debug(f"Determined mode: {mode}")

        transcript_path = hook_input.get("transcript_path", "")
        promise_just_cleared = False

        # Check for block report - if exists, archive it and allow exit
        blocked, _ = check_block_report()
        if blocked:
            logger.debug("Block report found, archiving and approving stop")
            archive_block_report()
            clear_promise_file()
            GURU_LOOP_PATH.unlink(missing_ok=True)
            SAMAYA_LOOP_PATH.unlink(missing_ok=True)
            _output_approve(course=course, waypoint=waypoint, clearing_promise=True)

        # L3/L2: Guru + Samaya ONLY fire at STARPORT zone
        # Design_Loop_Zone_Mapping: guru is the quality gate for leaving a starsystem.
        # HOME is unreachable while guru is active — you must prove emanation first.
        if mode == "STARPORT":
            # L3: Samaya loop (highest priority)
            samaya_active, _ = _check_samaya_loop()
            if samaya_active:
                logger.debug("L3 samaya loop active (STARPORT)")
                _handle_samaya_loop(transcript_path, course, waypoint)
                # If BREACHED, _handle_samaya_loop returns and we fall through to L2

            # L2: Guru loop
            guru_active, guru_content = _check_guru_loop()
            if guru_active:
                logger.debug("L2 guru loop active (STARPORT)")
                _handle_guru_loop(transcript_path, guru_content, course, waypoint)
                # _handle_guru_loop always blocks, never returns

        # L1: Promise check (existing behavior)
        # Check for <promise>DONE</promise> in transcript - if found, clear promise
        # but continue to check if SESSION/COURSE still active
        if check_done_in_transcript(transcript_path):
            logger.debug("DONE found in transcript, clearing promise")
            clear_promise_file()
            promise_just_cleared = True
            # Don't exit here - fall through to mode check

        _handle_promise_check(course, waypoint)
        _handle_mode_check(mode, course, waypoint, project_path, promise_just_cleared)

    except Exception as e:
        logger.error(f"Autopoiesis hook error: {e}\n{traceback.format_exc()}")
        _output_approve()


if __name__ == "__main__":
    main()
