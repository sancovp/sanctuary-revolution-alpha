#!/usr/bin/env python3
"""
OMNISANC Core - Foundational Workflow Enforcement

Always-on enforcement layer that structures sessions into:
- Home Mode: Global organizing space with limited tools, can plot_course
- Journey Mode: Working in a STARLOG project with full tools after orient()

This is the foundation layer that OMNISANC builds on top of.

=== KNOWN BUG: base_mission Auto-Activation Conflicts with HOME Mode ===

There's a state machine conflict between STARSYSTEM missions and omnisanc mode:

1. STARSYSTEM auto-creates/activates a `base_mission` on startup or trigger
2. Omnisanc sees mission.status == "active" and thinks we're in Journey/Mission mode
3. But starship.course_state says HOME because no plot_course was called
4. Result: Conflicting signals cause inconsistent blocking:
   - "Tool not allowed in Home Mode" (because course says HOME)
   - But also can't escape because "mission is active"

Root cause needs investigation:
- Where does base_mission get auto-activated?
- Should base_mission stay "pending" until mission_start() is called?
- Should omnisanc ignore base_mission when checking mode?
- Or should base_mission auto-creation be removed entirely?

The HOME mode invariant should be: NO active missions while in HOME.
================================================================================
"""

# KILL SWITCH CHECK - BEFORE ANY IMPORTS
# This must be first to avoid slow imports when OMNISANC is disabled
import os
import sys
import json

_KILL_SWITCH_FILE = "/tmp/heaven_data/omnisanc_core/.omnisanc_disabled"
if os.path.exists(_KILL_SWITCH_FILE):
    # OMNISANC disabled - pass through immediately, skip all heavy imports
    try:
        hook_data = json.load(sys.stdin)
        print(json.dumps({"decision": "allow", "reason": "omnisanc_disabled"}))
    except Exception:
        print(json.dumps({"decision": "allow", "reason": "omnisanc_disabled"}))
    sys.exit(0)

# TRACE AT FILE START - after kill switch check
from datetime import datetime
with open('/tmp/omnisanc_SCRIPT_START.log', 'a') as f:
    f.write(f"{datetime.now()} SCRIPT STARTED\n")
    f.flush()
import logging
from pathlib import Path
from datetime import datetime

# Set HEAVEN_DATA_DIR for registry access
os.environ["HEAVEN_DATA_DIR"] = "/tmp/heaven_data"

# Heaven registry for activity tracking and event logging
try:
    from heaven_base.registry.registry_service import RegistryService
    from heaven_base.registry.matryoshka_helper import (
        create_matryoshka_registry,
        add_to_matryoshka_layer
    )
    registry_service = RegistryService()
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    registry_service = None

# Mission module for session status updates
try:
    from starsystem import mission
    MISSION_AVAILABLE = True
except ImportError:
    MISSION_AVAILABLE = False
    mission = None

# GIINT module for JIT project construction
try:
    from llm_intelligence import projects as giint_projects
    from llm_intelligence.projects import ProjectType
    GIINT_AVAILABLE = True
except ImportError as e:
    # Log the import error for debugging
    with open('/tmp/omnisanc_giint_import_error.log', 'w') as f:
        f.write(f"GIINT import failed: {e}\n")
        import traceback
        f.write(traceback.format_exc())
    GIINT_AVAILABLE = False
    giint_projects = None
    ProjectType = None

# Canopy/OPERA hook integration
try:
    from canopy.omnisanc_hooks import (
        check_opera_lock,
        feed_from_opera_if_needed,
        trigger_pattern_detection_after_completion
    )
    CANOPY_OPERA_AVAILABLE = True
except ImportError:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Canopy/OPERA hooks not available - pattern detection and feeding disabled")
    CANOPY_OPERA_AVAILABLE = False
    check_opera_lock = None
    feed_from_opera_if_needed = None
    trigger_pattern_detection_after_completion = None

# Get logger
logger = logging.getLogger(__name__)
# Add file handler for GIINT-Carton hook debugging
file_handler = logging.FileHandler('/tmp/omnisanc_giint_debug.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

# Global state file
COURSE_STATE_FILE = "/tmp/heaven_data/omnisanc_core/.course_state"

def get_strata_mcp_env(server_name: str) -> dict:
    """
    Read Strata config and extract environment variables for an MCP server.

    Args:
        server_name: Name of the MCP server (e.g., "giint-llm-intelligence")

    Returns:
        Dictionary of environment variables for that server
    """
    try:
        strata_config_path = Path.home() / ".config" / "strata" / "servers.json"

        if not strata_config_path.exists():
            logger.warning(f"Strata config not found at {strata_config_path}")
            return {}

        with open(strata_config_path, 'r') as f:
            config = json.load(f)

        # Strata config format: {"mcp": {"servers": {"server_name": {...}}}}
        servers = config.get("mcp", {}).get("servers", {})
        server_config = servers.get(server_name, {})

        return server_config.get("env", {})

    except Exception as e:
        logger.error(f"Failed to read Strata config: {e}", exc_info=True)
        return {}

def _ensure_course_dir():
    """Ensure course state directory exists"""
    os.makedirs(os.path.dirname(COURSE_STATE_FILE), exist_ok=True)

def get_course_state() -> dict:
    """Get current course state"""
    _ensure_course_dir()

    try:
        if not os.path.exists(COURSE_STATE_FILE):
            return {
                "course_plotted": False,
                "projects": [],
                "flight_selected": False,
                "waypoint_step": 0,
                "session_active": False,
                "session_end_shield_count": 1,
                "session_shielded": True,
                "mission_active": False,
                "mission_id": None,
                "mission_step": 0,
                "last_oriented": None,
                "description": None,
                "domain": "HOME",  # NEW: Domain categorization
                "subdomain": None,  # NEW: Subdomain categorization
                "process": None,  # NEW: Specific process
                "needs_review": False,  # NEW: LANDING phase active flag
                "landing_routine_called": False,  # NEW: LANDING step 1
                "session_review_called": False,  # NEW: LANDING step 2
                "giint_respond_called": False  # NEW: LANDING step 3
            }

        with open(COURSE_STATE_FILE, 'r') as f:
            state = json.load(f)
            # Ensure waypoint_step exists for old state files
            if "waypoint_step" not in state:
                state["waypoint_step"] = 0
            # Ensure session_active exists for old state files
            if "session_active" not in state:
                state["session_active"] = False
            # Ensure session end shield fields exist for old state files
            if "session_end_shield_count" not in state:
                state["session_end_shield_count"] = 1
            if "session_shielded" not in state:
                state["session_shielded"] = True
            # Ensure mission fields exist for old state files
            if "mission_active" not in state:
                state["mission_active"] = False
            if "mission_id" not in state:
                state["mission_id"] = None
            if "mission_step" not in state:
                state["mission_step"] = 0
            # Ensure STARPORT fields exist for old state files (Phase 1)
            if "domain" not in state:
                state["domain"] = "HOME"
            if "subdomain" not in state:
                state["subdomain"] = None
            if "process" not in state:
                state["process"] = None
            # Ensure LANDING phase fields exist for old state files (Phase 2)
            if "needs_review" not in state:
                state["needs_review"] = False
            if "landing_routine_called" not in state:
                state["landing_routine_called"] = False
            if "session_review_called" not in state:
                state["session_review_called"] = False
            if "giint_respond_called" not in state:
                state["giint_respond_called"] = False
            return state
    except Exception as e:
        logger.error(f"Failed to read course state: {e}")
        return {
            "course_plotted": False,
            "projects": [],
            "flight_selected": False,
            "last_oriented": None,
            "description": None
        }

def save_course_state(state: dict):
    """Save course state"""
    _ensure_course_dir()

    try:
        with open(COURSE_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save course state: {e}")

def _get_waypoint_state(projects: list) -> dict:
    """Read actual waypoint state from Waypoint's JSON tracking."""
    if not projects:
        return {}

    # Get first project (primary working project)
    project_path = projects[0] if isinstance(projects, list) else projects
    project_name = Path(project_path).name

    # Read waypoint state JSON
    waypoint_state_file = f"/tmp/waypoint_state_{project_name}.json"
    try:
        if not os.path.exists(waypoint_state_file):
            return {}
        with open(waypoint_state_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read waypoint state: {e}")
        return {}

def ensure_event_registry(registry_base_name: str) -> bool:
    """
    Ensure matryoshka event registry exists with today's day layer.

    Args:
        registry_base_name: Base name like "home_events", "mission_events", "session_events"

    Returns:
        True if successful, False otherwise
    """
    if not REGISTRY_AVAILABLE:
        return False

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        matryoshka_name = registry_base_name
        coordinator_name = f"{matryoshka_name}_matryoshka"

        # Check if coordinator exists
        if not registry_service.simple_service.registry_exists(coordinator_name):
            # Create matryoshka with today as first subdomain
            create_matryoshka_registry(
                name=matryoshka_name,
                domain="omnisanc_events",
                seed_subdomains=[today]
            )
        else:
            # Coordinator exists, check if today's layer exists
            day_registry_name = f"{matryoshka_name}_{today}"
            if not registry_service.simple_service.registry_exists(day_registry_name):
                # Create today's layer
                registry_service.create_registry(day_registry_name)

                # Add metadata to day layer
                registry_service.add(
                    day_registry_name,
                    "_meta",
                    {
                        "domain": "omnisanc_events",
                        "subdomain": today,
                        "matryoshka_name": matryoshka_name,
                        "created_at": datetime.now().isoformat()
                    }
                )

                # Update coordinator's all_layers
                all_layers = registry_service.get(coordinator_name, "all_layers") or {}
                all_layers[today] = f"registry_all_ref={day_registry_name}"
                registry_service.update(coordinator_name, "all_layers", all_layers)

        return True
    except Exception as e:
        logger.error(f"Failed to ensure event registry {registry_base_name}: {e}")
        return False

def log_event(mode: str, tool_name: str, arguments: dict, allowed: bool, reason: str = "") -> None:
    """
    Log validation decision to appropriate event registry.

    Args:
        mode: "HOME", "JOURNEY_MISSION", or "JOURNEY_SESSION"
        tool_name: Tool that was validated
        arguments: Tool arguments (structured dict)
        allowed: Whether tool was allowed
        reason: Optional reason code for validation decision
    """
    if not REGISTRY_AVAILABLE:
        return

    try:
        # Determine which registry to log to
        if mode == "HOME":
            registry_base = "home_events"
        elif mode == "JOURNEY_MISSION":
            registry_base = "mission_events"
        elif mode == "JOURNEY_SESSION":
            registry_base = "session_events"
        else:
            logger.warning(f"Unknown mode for event logging: {mode}")
            return

        # Ensure registry exists
        if not ensure_event_registry(registry_base):
            return

        # Create event
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        event_key = f"event_{now.strftime('%Y%m%d_%H%M%S_%f')}"

        event_data = {
            "timestamp": now.isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "allowed": allowed,
            "mode": mode,
            "reason": reason
        }

        # Log to today's layer
        add_to_matryoshka_layer(
            matryoshka_name=registry_base,
            subdomain=today,
            key=event_key,
            value=event_data
        )

    except Exception as e:
        logger.error(f"Failed to log event: {e}")

# Home Mode tools (allowed when no course plotted)
# Only tools for HOME work - no actual project work allowed
HOME_MODE_TOOLS = {
    # Read/Search tools
    "Read",
    "Glob",
    "Grep",
    "Bash",  # Will validate mkdir/cd/ls/pwd commands separately

    # STARSHIP navigation
    "mcp__starship__plot_course",  # Enter Journey mode
    "mcp__starship__launch_routine",  # Learn about STARSHIP

    # SEED identity and guidance
    "mcp__seed__home",  # HOME HUD
    "mcp__seed__who_am_i",
    "mcp__seed__what_do_i_do",
    "mcp__seed__how_do_i",

    # Mission management (strategic planning at HOME)
    "mcp__STARSYSTEM__mission_create",
    "mcp__STARSYSTEM__mission_start",
    "mcp__STARSYSTEM__mission_get_status",
    "mcp__STARSYSTEM__mission_list",
    "mcp__STARSYSTEM__mission_request_extraction",
    "mcp__STARSYSTEM__view_mission_config",
    "mcp__STARSYSTEM__complete_mission",

    # GIINT core (cognitive infrastructure - always available)
    "mcp__giint-llm-intelligence__core__be_myself",  # Self-awareness gate - MUST be first every turn
    "mcp__be-myself__be_myself",  # Cognet self-awareness constraint tool

    # GIINT planning (cognitive infrastructure - always available)
    "mcp__giint-llm-intelligence__planning__create_project",
    "mcp__giint-llm-intelligence__planning__add_feature_to_project",
    "mcp__giint-llm-intelligence__planning__add_component_to_feature",
    "mcp__giint-llm-intelligence__planning__add_deliverable_to_component",
    "mcp__giint-llm-intelligence__planning__add_task_to_deliverable",

    # Canopy/OPERA (strategic work planning at HOME - Canopy references missions)
    "mcp__canopy__add_to_schedule",
    "mcp__canopy__view_schedule",
    "mcp__canopy__get_next_item",
    "mcp__canopy__mark_complete",
    "mcp__canopy__update_item_status",

    # OPERA pattern management (quarantine → golden → schedule)
    "mcp__opera__view_canopy_patterns",
    "mcp__opera__get_pattern_details",
    "mcp__opera__promote_pattern",
    "mcp__opera__view_operadic_flows",
    "mcp__opera__add_to_opera_schedule",
    "mcp__opera__view_opera_schedule",
    "mcp__opera__remove_from_opera_schedule",

    # OMNISANC observability (self-play system)
    "mcp__STARSYSTEM__check_selfplay_logs",
    "mcp__STARSYSTEM__get_fitness_score",
    "mcp__STARSYSTEM__toggle_omnisanc",

    # Registry tools (read-only metadata work)
    "mcp__heaven-framework-toolbox__registry_tool",
    "mcp__heaven-framework-toolbox__matryoshka_registry_tool",
  
    # Escape hatch - edit omnisanc_core.py from HOME if locked out
    "mcp__heaven-framework-toolbox__network_edit_tool",

    # Waypoint status checking (verify state before plotting course)
    "mcp__waypoint__get_waypoint_progress",
    "mcp__waypoint__abort_waypoint_journey",

    # Starship course state (read-only status check)
    "mcp__starship__get_course_state",

    # Carton knowledge graph (orientation and context)
    "mcp__carton__get_recent_concepts",
    "mcp__carton__query_wiki_graph",
    "mcp__carton__get_concept",
    "mcp__carton__get_concept_network",
    
    # TOOT (Train of Operadic Thought - context continuity)
    "mcp__toot__create_train_of_thought",
    "mcp__toot__update_train_of_thought",
    "mcp__toot__explain_train_of_thought",
}

def is_base_mission(state: dict) -> bool:
    """
    Check if base mission (implicit mission) is active.

    Base mission logic:
    - Course plotted (in Journey mode)
    - No explicit mission active
    - Session is active

    Base missions auto-capture work and persist across session ends.
    """
    return (state.get("course_plotted", False) and
            not state.get("mission_active", False) and
            state.get("session_active", False))

def is_safe_bash_command(arguments: dict) -> bool:
    """Check if bash command is mkdir, cd, ls, pwd, or escape hatch rm course_state"""
    command = arguments.get("command", "").strip()

    # Escape hatch: ONLY allow exact rm course_state command (never -rf)
    safe_rm_commands = [
        "rm /tmp/heaven_data/omnisanc_core/.course_state",
        "rm -f /tmp/heaven_data/omnisanc_core/.course_state"
    ]
    if command in safe_rm_commands:
        return True

    # Allow mkdir, cd, ls, pwd
    safe_commands = ["mkdir", "cd", "ls", "pwd"]
    return any(command.startswith(cmd) for cmd in safe_commands)

def validate_home_mode(tool_name: str, arguments: dict) -> dict:
    """Validate tool usage in Home Mode (no course plotted)"""

    # Check if tool is allowed in Home Mode
    if tool_name in HOME_MODE_TOOLS:
        # Special handling for Bash
        if tool_name == "Bash":
            if is_safe_bash_command(arguments):
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[🏠 HOME]: Only mkdir, cd, ls, pwd allowed in Home Mode. Plot a course with starship.plot_course() to access full tools."""
                }
        return {"allowed": True}

    # Tool not allowed in Home Mode
    return {
        "allowed": False,
        "error_message": f"""🏰🌐
[🏠 HOME]: Tool '{tool_name}' not allowed in Home Mode. Plot a course with starship.plot_course() to enter Journey Mode."""
    }

def validate_journey_mode(tool_name: str, state: dict) -> dict:
    """Validate tool usage in Journey Mode (course plotted)"""

    # Block extraction if session is active or waypoint journey in progress
    if tool_name == "mcp__STARSYSTEM__mission_request_extraction":
        if state.get("session_active", False):
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🛑 BLOCKED]: Cannot extract while session is active

You must end the session first:
1. starlog.end_starlog() - End current session
2. waypoint.abort_waypoint_journey() - Abort journey (if active)
3. mission.request_extraction() - Extract from mission

Then you can plot a new course if desired."""
            }

        # Check if waypoint journey exists (waypoint_step > 0 means journey started or active)
        waypoint_step = state.get("waypoint_step", 0)
        if waypoint_step > 0:
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🛑 BLOCKED]: Cannot extract while waypoint journey exists

You must abort the journey first:
1. waypoint.abort_waypoint_journey() - Abort journey
2. mission.request_extraction() - Extract from mission

Then you can plot a new course if desired."""
            }

    # Block mission creation/starting while on a course
    # Missions are atomic top-level loops - can't create/start while on any course
    if tool_name in ["mcp__STARSYSTEM__mission_create", "mcp__STARSYSTEM__mission_start"]:
        return {
            "allowed": False,
            "error_message": """🏰🌐
[🛑 BLOCKED]: Cannot create or start missions while on a course/mission

Missions are strategic planning activities that happen at HOME.

You must either:
1. starlog.end_starlog() - End current session (if active)
2. Return to HOME (course cleared)
3. Then plan/start missions at HOME

Or if on a mission:
1. mission.request_extraction() - Extract from current mission
2. Then create/start new mission at HOME"""
        }

    # Check if continue_course was called - must call orient
    if state.get("continue_course_called", False):
        if tool_name == "mcp__starlog__orient":
            return {"allowed": True}
        else:
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🔄 JOURNEY]: Reorientation required - call starlog.orient() to complete course continuation.

After calling continue_course(), you must call starlog.orient(path) to reload project context.
This clears the compact flag and you continue from where you left off."""
            }

    # Check if course was compacted (conversation was compacted)
    if state.get("was_compacted", False):
        # Must either continue_course() or plot_course() (which overwrites)
        if tool_name == "mcp__starship__continue_course":
            return {"allowed": True}
        elif tool_name == "mcp__starship__plot_course":
            return {"allowed": True}
        else:
            # Get projects list (backward compat with old project_path)
            projects = state.get('projects', [state.get('project_path', 'unknown')])
            if len(projects) == 1:
                projects_display = projects[0]
            else:
                projects_display = f"{len(projects)} projects"

            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🔄 JOURNEY]: Course compacted - choose how to proceed.

Current Course: {projects_display}

You must either:
1. starship.continue_course() - Resume the existing Journey
2. starship.plot_course() - Start a new Journey (overwrites current)

Cannot use other tools until you continue or plot a new course."""
            }

    # Check if LANDING phase must complete (sequential 3-step enforcement)
    if state.get("needs_review", False):
        landing_done = state.get("landing_routine_called", False)
        review_done = state.get("session_review_called", False)
        giint_done = state.get("giint_respond_called", False)

        # Step 1: Must call landing_routine first
        if not landing_done:
            if tool_name == "mcp__starship__landing_routine":
                return {"allowed": True}
            # Allow Canopy completion during LANDING Step 1
            elif tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[🛬 LANDING]: Step 1 of 3

Session ended. You must complete the 3-step LANDING sequence:

→ NEXT: starship.landing_routine() - Learn about LANDING phase
  Then: starship.session_review() - Review session and compose flight configs
  Then: giint.respond() - Capture mission intelligence (REQUIRED)

Only step 1 is allowed right now."""
                }

        # Step 2: Must call session_review second
        elif not review_done:
            if tool_name == "mcp__starship__session_review":
                return {"allowed": True}
            # Allow Canopy completion during LANDING Step 2
            elif tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[🛬 LANDING]: Step 2 of 3

✅ landing_routine() complete

→ NEXT: starship.session_review() - Review session and compose flight configs
  Then: giint.respond() - Capture mission intelligence (REQUIRED)

Only step 2 is allowed right now."""
                }

        # Step 3: Must call giint.respond last
        elif not giint_done:
            if tool_name == "mcp__giint-llm-intelligence__core__respond":
                return {"allowed": True}
            # Allow Canopy completion during LANDING Step 3
            elif tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
                return {"allowed": True}
            else:
                # Get qa_id and tracking context from state
                qa_id = state.get("qa_id", "UNKNOWN")
                mission_id = state.get("mission_id", "unknown")
                project_id = state.get("projects", ["unknown"])[0] if state.get("projects") else "unknown"
                domain = state.get("domain", "HOME")
                subdomain = state.get("subdomain", "unknown")

                return {
                    "allowed": False,
                    "error_message": f"""🏰🌐
[🛬 LANDING]: Step 3 of 3

✅ landing_routine() complete
✅ session_review() complete

→ NEXT: giint.respond() - Capture mission intelligence (REQUIRED)

QA Tracking Context:
  qa_id: "{qa_id}" (auto-linked to mission: {mission_id})
  project_id: "{project_id}" (COMPOSITE GIINT project - holds session intelligence)

Suggested GIINT Structure (customize as needed):
  feature: "mission_work"
  component: "uncategorized"
  deliverable: "session_intelligence"
  subtask: "session_capture"
  task: "capture"
  workflow_id: "{qa_id}"

NOTE: Mission has COMPOSITE project (container for session work).
If your session has a SINGLE GIINT project with planning/execution, that's separate.
These defaults are for intelligence capture only - JIT constructed when you call giint.respond().

This is the final step before returning to STARPORT."""
                }

    # Check if mission is active and session just ended (mission enforcement)
    if (state.get("mission_active", False) and
        state.get("waypoint_step", 0) == 0 and
        not state.get("session_active", False) and
        state.get("flight_selected")):

        # Allow mission management tools + abort for extraction cleanup
        if tool_name in ["mcp__STARSYSTEM__mission_get_status",
                         "mcp__STARSYSTEM__mission_inject_step",
                         "mcp__STARSYSTEM__mission_request_extraction",
                         "mcp__waypoint__abort_waypoint_journey"
                        ]:
            return {"allowed": True}

        # Allow waypoint.start to continue mission
        if tool_name == "mcp__waypoint__start_waypoint_journey":
            return {"allowed": True}

        # If waypoint journey is active (waypoint_step > 0), allow waypoint navigation
        # This allows check/orient/start_starlog to proceed after waypoint.start
        if state.get("waypoint_step", 0) > 0:
            if tool_name in ["mcp__waypoint__navigate_to_next_waypoint",
                             "mcp__starlog__check",
                             "mcp__starlog__orient",
                             "mcp__starlog__init_project",
                             "mcp__starlog__start_starlog"]:
                return {"allowed": True}

        # Allow fly() to browse flights
        if tool_name == "mcp__starship__fly":
            return {"allowed": True}

        # Allow Canopy completion between mission sessions
        if tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
            return {"allowed": True}

        # Block everything else - mission must continue
        mission_id = state.get("mission_id", "unknown")
        return {
            "allowed": False,
            "error_message": f"""🏰🌐
[🎯 MISSION]: Must continue mission sequence

Active Mission: {mission_id}

You must either:
1. mission.get_status('{mission_id}') - View next session details
2. waypoint.start_waypoint_journey() - Start next session in sequence
3. mission.inject_step() - Add prerequisite step before current
4. mission.request_extraction() - Abort mission and reset to HOME

Cannot use other tools until mission is continued or extracted."""
        }

    # Check if fly has been called (enables waypoint.start)
    if not state.get("fly_called", False):
        # Can call fly() or launch() to proceed
        if tool_name in ["mcp__starship__fly", "mcp__starship__launch_routine"]:
            return {"allowed": True}
        # Allow Canopy completion during STARPORT Part 1 (LAUNCH)
        elif tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
            return {"allowed": True}
        else:
            # Get projects list
            projects = state.get('projects')
            if projects:
                if len(projects) == 1:
                    projects_msg = f"Project: {projects[0]}"
                else:
                    projects_msg = "Projects:\n" + "\n".join(f"  - {p}" for p in projects)
            else:
                projects_msg = f"Project: {state.get('project_path', 'unknown')}"

            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🗺️ STARPORT]: COURSE PLOTTED: Must browse flight configurations to proceed.

Course plotted:
{projects_msg}

Choose your path:
1. starship.fly() - Browse available flight configurations
2. starship.launch_routine() - Learn about STARSHIP and flights

After calling fly(), you can start a waypoint journey."""
            }

    # Check if flight selected (waypoint.start called)
    if not state.get("flight_selected", False):
        # STARPORT entry check: If no mission, auto-clear course → HOME
        if not state.get("mission_active", False) and state.get("course_plotted", True):
            state["course_plotted"] = False
            state["projects"] = []
            state["description"] = None
            state["domain"] = "HOME"
            state["subdomain"] = None
            state["process"] = None
            save_course_state(state)
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🏠 HOME]: RETURNED TO HOME: Journey complete

No active mission detected at STARPORT.
Course cleared - you are now in HOME mode.

Plot a new course with starship.plot_course() when ready."""
            }

        # Always allow fly() to browse available flights
        if tool_name == "mcp__starship__fly":
            return {"allowed": True}

        # Can call waypoint.start to begin journey
        if tool_name == "mcp__waypoint__start_waypoint_journey":
            return {"allowed": True}

        # Always allow toggle_omnisanc (escape hatch)
        if tool_name == "mcp__STARSYSTEM__toggle_omnisanc":
            return {"allowed": True}

        # Allow mission management, home, and Canopy completion in this state
        if tool_name in {"mcp__STARSYSTEM__complete_mission", "mcp__STARSYSTEM__mission_get_status", "mcp__STARSYSTEM__mission_list", "mcp__seed__home", "mcp__canopy__mark_complete", "mcp__canopy__update_item_status"}:
            return {"allowed": True}
        else:
            # Get course details for informative message
            projects = state.get('projects')
            if projects:
                if len(projects) == 1:
                    projects_msg = f"Project: {projects[0]}"
                else:
                    projects_msg = "Projects:\n" + "\n".join(f"  - {p}" for p in projects)
            else:
                projects_msg = f"Project: {state.get('project_path', 'unknown')}"

            description = state.get('description', 'No description provided')

            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🗺️ STARPORT]: JOURNEY MODE - STARPORT Phase

Course Details:
{projects_msg}
Description: {description}

Current Phase: STARPORT - Selecting flight configuration
- Call starship.fly() to browse available flight configs (can call multiple times)
- When ready, call waypoint.start_waypoint_journey(config_path, starlog_path) to begin

Available tools in this phase:
- starship.fly() - Browse/explore flight configurations
- mission.get_status() / mission.list() - View mission details
- seed.home() - View HOME HUD
- starship.get_course_state() - See full course state

Next step: Choose a flight config and start your waypoint journey."""
            }

    # Waypoint step enforcement (after flight selected)
    # Read actual waypoint state from Waypoint's JSON tracking
    waypoint_state = _get_waypoint_state(state.get("projects", []))
    if not waypoint_state:
        waypoint_step = 0
    else:
        waypoint_step = waypoint_state.get("completed_count", 0)

    if waypoint_step > 0 and waypoint_step < 4:
        # Step 1: We've been served check.md, must call check() or navigate()
        if waypoint_step == 1:
            if tool_name == "mcp__starlog__check":
                return {"allowed": True}
            elif tool_name == "mcp__waypoint__navigate_to_next_waypoint":
                # Allow navigate between steps
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[✈️ SESSION]: Waypoint Step 1: Must call starlog.check() to verify project exists, then navigate_to_next_waypoint()"""
                }

        # Step 2: We've been served orient.md, must call orient/init or navigate()
        elif waypoint_step == 2:
            if tool_name == "mcp__starlog__orient":
                return {"allowed": True}
            elif tool_name == "mcp__starlog__init_project":
                # Allow init if project doesn't exist
                return {"allowed": True}
            elif tool_name == "mcp__waypoint__navigate_to_next_waypoint":
                # Allow navigate between steps
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[✈️ SESSION]: Waypoint Step 2: Must call starlog.orient() to load project context OR starlog.init_project() if project doesn't exist, then navigate_to_next_waypoint()"""
                }

        # Step 3: We've been served start_session.md, must call start_starlog() or navigate()
        elif waypoint_step == 3:
            if tool_name == "mcp__starlog__start_starlog":
                state["session_active"] = True  # Track active session
                save_course_state(state)
                return {"allowed": True}
            elif tool_name == "mcp__waypoint__navigate_to_next_waypoint":
                # Allow navigate between steps
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[✈️ SESSION]: Waypoint Step 3: Must call starlog.start_starlog() to begin session (WARPCORE activates), then navigate_to_next_waypoint()"""
                }

    # Step 4 or waypoint not started - allow all tools
    return {"allowed": True}

def on_tool_use(tool_name: str, arguments: dict) -> dict:
    """
    OMNISANC Core hook - enforces Home/Journey workflow

    Returns:
        dict with 'allowed' boolean and optional 'error_message'
    """
    try:
        # KILL SWITCH: If .omnisanc_disabled exists, allow all tools
        kill_switch_file = "/tmp/heaven_data/omnisanc_core/.omnisanc_disabled"
        if os.path.exists(kill_switch_file):
            return {"allowed": True}

        # STRATA META-TOOLS WHITELIST: Always allow discovery/docs tools
        # These are read-only tools for exploring what's available
        # Only execute_action needs validation (it's the actual tool execution)
        strata_meta_tools_whitelist = [
            "mcp__strata__discover_server_actions",
            "mcp__strata__get_action_details",
            "mcp__strata__search_documentation",
            "mcp__strata__handle_auth_failure"
        ]
        if tool_name in strata_meta_tools_whitelist:
            return {"allowed": True, "reason": "strata_meta_tool_whitelisted"}

        # SKILL MANAGER WHITELIST: Always allow skill operations
        # Skills are the entry point to everything - should never be blocked
        if tool_name == "mcp__skill_manager_treeshell__run_conversation_shell":
            return {"allowed": True, "reason": "skill_manager_whitelisted"}

        # GNOSYS-KIT WHITELIST: Always allow gnosys-kit meta operations
        # execute_action calls get unwrapped and validated as the actual tool
        # Other commands (nav, manage_servers, discover_server_actions) are always allowed
        if tool_name == "mcp__gnosys_kit__run_conversation_shell":
            return {"allowed": True, "reason": "gnosys_kit_whitelisted"}

        # OMNISANC TOGGLE WHITELIST: Always allow toggling OMNISANC on/off
        # This ensures users can always disable OMNISANC if needed
        if tool_name == "mcp__STARSYSTEM__toggle_omnisanc":
            return {"allowed": True, "reason": "omnisanc_toggle_whitelisted"}

        state = get_course_state()

        # ESCAPE HATCH: Allow rm .course_state to bypass ALL validation
        # This must run BEFORE any other checks to recover from deadlock states
        if tool_name == "Bash" and is_safe_bash_command(arguments):
            command = arguments.get("command", "").strip()
            safe_rm_commands = [
                "rm /tmp/heaven_data/omnisanc_core/.course_state",
                "rm -f /tmp/heaven_data/omnisanc_core/.course_state"
            ]
            if command in safe_rm_commands:
                return {"allowed": True}

        # SESSION END SHIELD: Prevent auto-ending sessions after compaction
        if tool_name == "mcp__starlog__end_starlog":
            shielded = state.get("session_shielded", True)
            shield_count = state.get("session_end_shield_count", 1)

            if shielded and shield_count > 0:
                # Decrement shield count
                state["session_end_shield_count"] = shield_count - 1
                save_course_state(state)

                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[🛡️ BLOCKED]: SESSION END SHIELD: Cannot end session without explicit authorization.

Ask the user what they want to do next instead of automatically ending the session.

This protection prevents auto-ending sessions after conversation compaction."""
                }

        # JIT GIINT PROJECT CONSTRUCTION: Before giint.respond(), auto-create project hierarchy
        if tool_name == "mcp__giint-llm-intelligence__core__respond" and GIINT_AVAILABLE:
            try:
                project_id = arguments.get("project_id")
                feature = arguments.get("feature")
                component = arguments.get("component")
                deliverable = arguments.get("deliverable")
                task = arguments.get("task")

                if project_id and feature and component and deliverable and task:
                    # JIT construct the hierarchy
                    # Step 1: Ensure feature exists
                    try:
                        giint_projects.add_feature_to_project(project_id, feature)
                        logger.info(f"JIT: Added feature '{feature}' to project '{project_id}'")
                    except Exception as e:
                        # Feature might already exist
                        logger.debug(f"JIT: Feature might already exist: {e}")

                    # Step 2: Ensure component exists in feature
                    try:
                        giint_projects.add_component_to_feature(project_id, feature, component)
                        logger.info(f"JIT: Added component '{component}' to feature '{feature}'")
                    except Exception as e:
                        logger.debug(f"JIT: Component might already exist: {e}")

                    # Step 3: Ensure deliverable exists in component
                    try:
                        giint_projects.add_deliverable_to_component(project_id, feature, component, deliverable)
                        logger.info(f"JIT: Added deliverable '{deliverable}' to component '{component}'")
                    except Exception as e:
                        logger.debug(f"JIT: Deliverable might already exist: {e}")

                    # Step 4: Ensure task exists in deliverable
                    try:
                        giint_projects.add_task_to_deliverable(
                            project_id, feature, component, deliverable, task,
                            is_human_only_task=False,
                            agent_id="llm_agent"
                        )
                        logger.info(f"JIT: Added task '{task}' to deliverable '{deliverable}'")
                    except Exception as e:
                        logger.debug(f"JIT: Task might already exist: {e}")

                    logger.info(f"JIT construction complete for {project_id}/{feature}/{component}/{deliverable}/{task}")
            except Exception as e:
                logger.error(f"JIT GIINT construction failed: {e}", exc_info=True)
                # Don't block the call - JIT is best-effort

        # Enforce mission lock - cannot plot_course while mission actively engaged
        if tool_name == "mcp__starship__plot_course" and state.get("mission_active", False):
            mission_id = state.get("mission_id", "unknown")
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🎯 MISSION]: MISSION LOCKED: Cannot change course while mission is actively engaged

Active Mission: {mission_id}

You must extract from the mission first using:
mission.request_extraction('{mission_id}')

After extraction, you can plot a new course (which will end the paused mission)."""
            }

        # Canopy/OPERA pre-tool lock - prevent freestyle additions when OPERA has work
        if tool_name == "mcp__canopy__add_to_schedule" and CANOPY_OPERA_AVAILABLE:
            try:
                source_type = arguments.get("source_type", "freestyle")
                lock_error = check_opera_lock(source_type)

                if lock_error:
                    # Log lock enforcement
                    log_event(
                        mode="JOURNEY_SESSION",
                        tool_name=tool_name,
                        arguments=arguments,
                        allowed=False,
                        reason="opera_schedule_lock_active"
                    )

                    return {
                        "allowed": False,
                        "error_message": lock_error
                    }
            except Exception as e:
                logger.error(f"Canopy/OPERA lock check failed (non-critical): {e}", exc_info=True)
                # Don't block on hook failure

        # Determine current mode for event logging
        if not state.get("course_plotted", False):
            current_mode = "HOME"
        elif state.get("session_active", False):
            current_mode = "JOURNEY_SESSION"
        elif state.get("mission_active", False):
            current_mode = "JOURNEY_MISSION"
        else:
            current_mode = "JOURNEY_SESSION"  # Default to session for journey without mission

        # Check mode and validate
        if not state.get("course_plotted", False):
            # Home Mode - limited tools
            result = validate_home_mode(tool_name, arguments)

            # Log event
            log_event(
                mode=current_mode,
                tool_name=tool_name,
                arguments=arguments,
                allowed=result.get("allowed", False),
                reason=result.get("error_message", "") if not result.get("allowed", False) else "home_mode_allowed"
            )

            return result
        else:
            # Journey Mode - follow flight sequence
            result = validate_journey_mode(tool_name, state)

            # Track when waypoint journey starts (unlocks Journey mode)
            if tool_name == "mcp__waypoint__start_waypoint_journey" and result.get("allowed", False):
                state["flight_selected"] = True
                state["waypoint_step"] = 1  # Initialize waypoint sequence
                save_course_state(state)

                # Track last_flight to registry
                if REGISTRY_AVAILABLE and arguments:
                    config_path = arguments.get("config_path", "unknown")
                    starlog_path = arguments.get("starlog_path", "unknown")

                    try:
                        # Ensure registry exists
                        if not registry_service.simple_service.registry_exists("last_activity_tracking"):
                            registry_service.create_registry("last_activity_tracking")

                        # Use add if first time, update if exists
                        flight_data = {
                            "config_path": config_path,
                            "starlog_path": starlog_path,
                            "timestamp": datetime.now().isoformat()
                        }

                        if not registry_service.add("last_activity_tracking", "last_flight", flight_data):
                            # Key exists, update it
                            registry_service.update("last_activity_tracking", "last_flight", flight_data)
                    except Exception as e:
                        logger.error(f"Failed to track last_flight: {e}")

            # Track when fly() is called (enables waypoint.start)
            if tool_name == "mcp__starship__fly" and result.get("allowed", False):
                state["fly_called"] = True
                save_course_state(state)

            # Track when continue_course() is called
            if tool_name == "mcp__starship__continue_course" and result.get("allowed", False):
                state["continue_course_called"] = True
                save_course_state(state)

            # Track when orient() is called after continue_course
            if tool_name == "mcp__starlog__orient" and result.get("allowed", False):
                if state.get("continue_course_called", False):
                    state["was_compacted"] = False
                    state["continue_course_called"] = False
                    save_course_state(state)

            # Track LANDING phase tool completions
            if tool_name == "mcp__starship__landing_routine" and result.get("allowed", False):
                if state.get("needs_review", False):
                    state["landing_routine_called"] = True
                    save_course_state(state)

            if tool_name == "mcp__starship__session_review" and result.get("allowed", False):
                if state.get("needs_review", False):
                    state["session_review_called"] = True
                    save_course_state(state)

            if tool_name == "mcp__giint-llm-intelligence__core__respond" and result.get("allowed", False):
                if state.get("needs_review", False):
                    state["giint_respond_called"] = True
                    state["needs_review"] = False  # Exit LANDING phase
                    # Reset flags for next LANDING
                    state["landing_routine_called"] = False
                    state["session_review_called"] = False
                    state["giint_respond_called"] = False
                    save_course_state(state)

            # Track when session ends
            if tool_name == "mcp__starlog__end_starlog" and result.get("allowed", False):
                state["session_active"] = False
                state["waypoint_step"] = 0  # No session = no waypoint journey
                state["flight_selected"] = False  # Reset for next journey
                state["fly_called"] = False  # Reset fly state - return to course plotted
                state["session_end_shield_count"] = 1  # Reset shield for next session
                state["session_shielded"] = True  # Re-enable shield
                state["needs_review"] = True  # Enter LANDING phase
                state["landing_routine_called"] = False  # Reset step tracking
                state["session_review_called"] = False
                state["giint_respond_called"] = False
                save_course_state(state)

                # Update mission session status to completed
                if state.get("mission_active", False) and MISSION_AVAILABLE:
                    mission_id = state.get("mission_id")
                    if mission_id:
                        try:
                            loaded_mission = mission.load_mission(mission_id)
                            if loaded_mission:
                                current_step = loaded_mission.current_step
                                if current_step < len(loaded_mission.session_sequence):
                                    # Mark current session as completed
                                    loaded_mission.session_sequence[current_step].status = "completed"
                                    loaded_mission.session_sequence[current_step].completed_at = datetime.now().isoformat()
                                    loaded_mission.metrics.sessions_completed += 1
                                    mission.save_mission(loaded_mission)
                                    logger.info(f"Marked mission session {current_step} as completed")
                        except Exception as e:
                            logger.error(f"Failed to update mission session status: {e}")

            # Track when plot_course is allowed (PreToolUse)
            # Actual state update happens in PostToolUse after success

            # Track when mission starts
            if tool_name == "mcp__STARSYSTEM__mission_start" and result.get("allowed", False):
                # Mission activation happens at HOME, triggers journey mode with mission enforcement
                # The mission_id will be passed in arguments
                mission_id = arguments.get("mission_id")
                if mission_id:
                    # Load mission to extract projects
                    mission_file = f"/tmp/heaven_data/missions/{mission_id}.json"
                    try:
                        with open(mission_file, 'r') as f:
                            mission_data = json.load(f)
                            # Extract unique project paths from session sequence
                            projects = list(set(
                                session["project_path"]
                                for session in mission_data["session_sequence"]
                            ))
                            state["projects"] = projects
                    except Exception as e:
                        logger.error(f"Failed to load mission projects: {e}")
                        state["projects"] = []

                    state["mission_active"] = True
                    state["mission_id"] = mission_id
                    state["mission_step"] = 0
                    # Mission start also plots course and activates journey
                    state["course_plotted"] = True
                    save_course_state(state)

            # Track when mission extraction is allowed (PreToolUse)
            # Actual state clearing happens in PostToolUse after extraction succeeds

            # Handle waypoint abort - check for active session first
            if tool_name == "mcp__waypoint__abort_waypoint_journey":
                if state.get("session_active", False):
                    abort_result = {
                        "allowed": False,
                        "error_message": """🏰🌐
[🛑 BLOCKED]: SESSION IN PROGRESS: Cannot abort while STARLOG session is active.

You must end the session first using starlog.end_starlog().
Explain your abort reason in the session end entry."""
                    }

                    # Log event
                    log_event(
                        mode=current_mode,
                        tool_name=tool_name,
                        arguments=arguments,
                        allowed=False,
                        reason="session_active_blocks_abort"
                    )

                    return abort_result
                elif result.get("allowed", False):
                    # No active session, proceed with abort
                    state["flight_selected"] = False
                    state["waypoint_step"] = 0
                    # If mission active, this is ratcheting - stay at current mission step
                    if state.get("mission_active", False):
                        # Ratcheting: abort resets waypoint but keeps mission at current step
                        # User can retry same step or inject new steps
                        pass  # mission_step stays unchanged
                    save_course_state(state)

            # Waypoint journey completion does NOT reset course state
            # Course remains plotted after waypoint journeys complete
            # Only plot_course, mission extraction, or manual state clear resets course

            # Log journey mode event
            log_event(
                mode=current_mode,
                tool_name=tool_name,
                arguments=arguments,
                allowed=result.get("allowed", False),
                reason=result.get("error_message", "")[:100] if not result.get("allowed", False) else "journey_mode_allowed"
            )

            return result

    except Exception as e:
        logger.error(f"OMNISANC Core error: {e}")

        # Try to log error event
        try:
            state = get_course_state()
            if not state.get("course_plotted", False):
                error_mode = "HOME"
            elif state.get("session_active", False):
                error_mode = "JOURNEY_SESSION"
            elif state.get("mission_active", False):
                error_mode = "JOURNEY_MISSION"
            else:
                error_mode = "JOURNEY_SESSION"

            log_event(
                mode=error_mode,
                tool_name=tool_name,
                arguments=arguments,
                allowed=True,
                reason=f"omnisanc_error_failopen: {str(e)[:100]}"
            )
        except Exception as log_error:
            logger.error(f"Failed to log error event: {log_error}")

        # Fail open - allow tool on error
        return {"allowed": True, "reason": f"OMNISANC Core error - allowed by default: {str(e)}"}

def on_tool_result(tool_name: str, arguments: dict, result: any) -> dict:
    """
    OMNISANC PostToolUseHook - fires after tool completes
    
    Handles:
    - Session score computation after end_starlog
    - Mission score computation after request_extraction
    
    Returns:
        dict with any post-processing results
    """
    try:
        # Update course state after plot_course succeeds
        if tool_name == "mcp__starship__plot_course":
            state = get_course_state()

            # If there's a paused mission (mission_active=False but mission_id set), clear it
            if not state.get("mission_active", False) and state.get("mission_id"):
                state["mission_id"] = None
                state["mission_step"] = 0

            # Update course state to Journey mode
            state["course_plotted"] = True

            # Extract project paths from arguments
            project_paths = arguments.get("project_paths", [])
            if isinstance(project_paths, str):
                project_paths = [project_paths]
            state["projects"] = project_paths

            # Store description
            state["description"] = arguments.get("description", None)

            # Store STARPORT fields (Phase 1)
            state["domain"] = arguments.get("domain") or "HOME"
            state["subdomain"] = arguments.get("subdomain")
            state["process"] = arguments.get("process")

            # Generate qa_id for base mission (plot_course creates base mission with mission_id)
            mission_id = state.get("mission_id")
            if mission_id:
                qa_id = f"{mission_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                state["qa_id"] = qa_id
                logger.info(f"Generated qa_id for base mission: {qa_id}")

                # Auto-create COMPOSITE GIINT project for base mission (JIT construction)
                if GIINT_AVAILABLE:
                    try:
                        project_dir = project_paths[0] if project_paths else "/tmp/unknown"
                        giint_projects.create_project(
                            project_id=mission_id,
                            project_dir=project_dir,
                            starlog_path=project_dir,
                            project_type=ProjectType.COMPOSITE
                        )
                        logger.info(f"Auto-created COMPOSITE GIINT project for base mission: {mission_id}")
                    except Exception as e:
                        logger.error(f"Failed to create GIINT project for base mission: {e}", exc_info=True)

            save_course_state(state)
            logger.info(f"Course state updated: {project_paths} [domain={state['domain']}, subdomain={state['subdomain']}, process={state['process']}]")

        # Generate qa_id after mission_start succeeds
        if tool_name == "mcp__STARSYSTEM__mission_start":
            state = get_course_state()
            mission_id = state.get("mission_id")
            if mission_id:
                qa_id = f"{mission_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                state["qa_id"] = qa_id
                save_course_state(state)
                logger.info(f"Generated qa_id for formal mission: {qa_id}")

                # Auto-create COMPOSITE GIINT project for formal mission (JIT construction)
                if GIINT_AVAILABLE:
                    try:
                        projects = state.get("projects", [])
                        project_dir = projects[0] if projects else "/tmp/unknown"
                        giint_projects.create_project(
                            project_id=mission_id,
                            project_dir=project_dir,
                            starlog_path=project_dir,
                            project_type=ProjectType.COMPOSITE
                        )
                        logger.info(f"Auto-created COMPOSITE GIINT project for formal mission: {mission_id}")
                    except Exception as e:
                        logger.error(f"Failed to create GIINT project for formal mission: {e}", exc_info=True)

        # Clear mission state after extraction succeeds
        if tool_name == "mcp__STARSYSTEM__mission_request_extraction":
            state = get_course_state()

            # Pause mission - return to HOME but keep mission_id (top of queue)
            state["mission_active"] = False
            # Keep mission_id - mission paused, can resume or end by plotting new course
            state["mission_step"] = 0
            state["course_plotted"] = False
            state["flight_selected"] = False
            state["fly_called"] = False
            state["waypoint_step"] = 0

            save_course_state(state)
            logger.info("Mission extraction completed - state cleared to HOME")

        # Return to HOME after mission completion
        if tool_name == "mcp__STARSYSTEM__complete_mission":
            state = get_course_state()

            # Mission complete - return to HOME and clear all state
            state["mission_active"] = False
            state["mission_id"] = None
            state["mission_step"] = 0
            state["course_plotted"] = False
            state["flight_selected"] = False
            state["fly_called"] = False
            state["waypoint_step"] = 0
            state["projects"] = []

            save_course_state(state)
            logger.info("Mission completed - returned to HOME")

            # Auto-complete Canopy items referencing this completed mission
            if CANOPY_OPERA_AVAILABLE:
                try:
                    from canopy.core import get_schedule_registry_data, mark_item_complete

                    completed_mission_id = arguments.get("mission_id")
                    if completed_mission_id:
                        # Get all Canopy schedule items
                        schedule_data = get_schedule_registry_data()

                        # Find items referencing this mission
                        for item_id, item_data in schedule_data.items():
                            if item_id == "_meta":
                                continue

                            # Check if this item references the completed mission
                            metadata = item_data.get("metadata", {})
                            item_mission_id = metadata.get("mission_id")

                            if item_mission_id == completed_mission_id:
                                # Auto-complete the Canopy item
                                try:
                                    mark_item_complete(item_id)
                                    logger.info(f"Auto-completed Canopy item {item_id} (mission {completed_mission_id} completed)")
                                except Exception as e:
                                    logger.error(f"Failed to auto-complete Canopy item {item_id}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to auto-complete Canopy items after mission completion: {e}", exc_info=True)

        # Session scoring after end_starlog
        if tool_name == "mcp__starlog__end_starlog" and REGISTRY_AVAILABLE:
            try:
                # Get today's date
                today = datetime.now().strftime("%Y-%m-%d")
                
                # Get session events from today's session registry
                from starsystem.reward_system import get_events_from_registry, compute_session_reward
                
                session_events = get_events_from_registry(registry_service, "session_events", today)
                
                if session_events:
                    # Compute session score
                    session_score = compute_session_reward(session_events)
                    
                    # Store score in session_scores registry
                    if not registry_service.simple_service.registry_exists("session_scores"):
                        registry_service.create_registry("session_scores")
                    
                    # Extract project path and session context from arguments
                    project_path = arguments.get("path", "unknown")
                    
                    score_entry = {
                        "project_path": project_path,
                        "raw_score": session_score,
                        "timestamp": datetime.now().isoformat(),
                        "event_count": len(session_events),
                        "computation_trace": {
                            "events_counted": len(session_events),
                            "formula": "sum(event_rewards) * SESSION_MULTIPLIER * quality_factor"
                        }
                    }
                    
                    # Use timestamp as key for uniqueness
                    score_key = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                    registry_service.add("session_scores", score_key, score_entry)

                    # Track as last_score for easy access
                    if not registry_service.simple_service.registry_exists("last_activity_tracking"):
                        registry_service.create_registry("last_activity_tracking")

                    last_score_data = {
                        "score": session_score,
                        "type": "session",
                        "timestamp": datetime.now().isoformat(),
                        "project_path": project_path
                    }

                    if not registry_service.add("last_activity_tracking", "last_score", last_score_data):
                        registry_service.update("last_activity_tracking", "last_score", last_score_data)

                    logger.info(f"Session score computed: {session_score} ({len(session_events)} events)")
                    
            except Exception as e:
                logger.error(f"Failed to compute session score: {e}")
        
        # Mission scoring after request_extraction
        elif tool_name == "mcp__STARSYSTEM__mission_request_extraction" and REGISTRY_AVAILABLE:
            try:
                # Get today's date
                today = datetime.now().strftime("%Y-%m-%d")
                
                # Get mission events from today's mission registry
                from starsystem.reward_system import get_events_from_registry, compute_mission_reward
                
                mission_events = get_events_from_registry(registry_service, "mission_events", today)
                
                if mission_events:
                    # Compute mission score
                    mission_score = compute_mission_reward(mission_events)
                    
                    # Store score in mission_scores registry
                    if not registry_service.simple_service.registry_exists("mission_scores"):
                        registry_service.create_registry("mission_scores")
                    
                    # Extract mission_id from arguments
                    mission_id = arguments.get("mission_id", "unknown")
                    
                    score_entry = {
                        "mission_id": mission_id,
                        "raw_score": mission_score,
                        "timestamp": datetime.now().isoformat(),
                        "event_count": len(mission_events),
                        "computation_trace": {
                            "events_counted": len(mission_events),
                            "formula": "sum(event_rewards) * MISSION_MULTIPLIER"
                        }
                    }
                    
                    # Use mission_id as key
                    score_key = f"miss_{mission_id}"
                    registry_service.add("mission_scores", score_key, score_entry)
                    
                    logger.info(f"Mission score computed: {mission_score} ({len(mission_events)} events)")
                    
            except Exception as e:
                logger.error(f"Failed to compute mission score: {e}")

        # Canopy/OPERA post-tool hooks - feeding and pattern detection
        if CANOPY_OPERA_AVAILABLE:
            # Hook triggers after Canopy item completion
            if tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
                try:
                    # Check if item was actually completed
                    item_completed = (
                        tool_name == "mcp__canopy__mark_complete" or
                        arguments.get("status") == "completed"
                    )

                    if item_completed:
                        # Pattern detection: Run after each completion
                        try:
                            detection_result = trigger_pattern_detection_after_completion()
                            if detection_result.get("success"):
                                detected = detection_result.get("detected_patterns", 0)
                                stored = detection_result.get("stored_patterns", 0)
                                logger.info(f"Pattern detection: {detected} patterns detected, {stored} stored to quarantine")
                        except Exception as e:
                            logger.error(f"Pattern detection failed (non-critical): {e}", exc_info=True)

                        # Feeding: Auto-expand OPERA items when Canopy is low
                        try:
                            feed_result = feed_from_opera_if_needed()
                            if feed_result.get("success") and feed_result.get("fed_count", 0) > 0:
                                fed_count = feed_result.get("fed_count")
                                fed_items = feed_result.get("fed_items", [])
                                logger.info(f"OPERA feeding: Added {fed_count} items to Canopy: {fed_items}")
                        except Exception as e:
                            logger.error(f"OPERA feeding failed (non-critical): {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"Canopy/OPERA post-tool hooks failed (non-critical): {e}", exc_info=True)

        # GIINT-Carton sync hooks - dual-write pattern
        print(f"🔍 [GIINT-Carton Hook] GIINT_AVAILABLE={GIINT_AVAILABLE}, tool_name={tool_name}", file=sys.stderr)
        logger.info(f"[GIINT-Carton Hook] GIINT_AVAILABLE={GIINT_AVAILABLE}, tool_name={tool_name}")
        if GIINT_AVAILABLE:
            giint_tool_mappings = {
                "mcp__giint-llm-intelligence__planning__create_project": "sync_project",
                "mcp__giint-llm-intelligence__planning__add_feature_to_project": "sync_feature",
                "mcp__giint-llm-intelligence__planning__add_component_to_feature": "sync_component",
                "mcp__giint-llm-intelligence__planning__add_deliverable_to_component": "sync_deliverable",
                "mcp__giint-llm-intelligence__planning__add_task_to_deliverable": "sync_task",
            }

            logger.info(f"[GIINT-Carton Hook] PostToolUse fired for tool: {tool_name}")
            if tool_name in giint_tool_mappings:
                logger.info(f"[GIINT-Carton Hook] Tool matched! Sync type: {giint_tool_mappings[tool_name]}")
                try:
                    # Import carton_sync module
                    from llm_intelligence import carton_sync

                    sync_type = giint_tool_mappings[tool_name]

                    # Extract project data and call appropriate sync function
                    project_id = arguments.get("project_id")
                    if not project_id:
                        logger.warning("GIINT sync skipped: no project_id in arguments")
                    else:
                        # Load project from GIINT registry
                        try:
                            project_data = giint_projects.get_project(project_id)
                            if not project_data.get("success"):
                                logger.error(f"Failed to load GIINT project {project_id}")
                            else:
                                project = project_data.get("project")

                                # Call appropriate sync function based on tool
                                if sync_type == "sync_project":
                                    sync_result = carton_sync.sync_project_to_carton(project)
                                    logger.info(f"Synced GIINT project '{project_id}' to Carton")

                                elif sync_type == "sync_feature":
                                    feature_name = arguments.get("feature_name")
                                    if feature_name and feature_name in project.get("features", {}):
                                        feature_data = project["features"][feature_name]
                                        sync_result = carton_sync.sync_feature_to_carton(project_id, feature_name, feature_data)
                                        logger.info(f"Synced GIINT feature '{project_id}/{feature_name}' to Carton")

                                elif sync_type == "sync_component":
                                    feature_name = arguments.get("feature_name")
                                    component_name = arguments.get("component_name")
                                    if feature_name and component_name:
                                        feature_data = project.get("features", {}).get(feature_name, {})
                                        component_data = feature_data.get("components", {}).get(component_name, {})
                                        if component_data:
                                            sync_result = carton_sync.sync_component_to_carton(project_id, feature_name, component_name, component_data)
                                            logger.info(f"Synced GIINT component '{project_id}/{feature_name}/{component_name}' to Carton")

                                elif sync_type == "sync_deliverable":
                                    feature_name = arguments.get("feature_name")
                                    component_name = arguments.get("component_name")
                                    deliverable_name = arguments.get("deliverable_name")
                                    if feature_name and component_name and deliverable_name:
                                        feature_data = project.get("features", {}).get(feature_name, {})
                                        component_data = feature_data.get("components", {}).get(component_name, {})
                                        deliverable_data = component_data.get("deliverables", {}).get(deliverable_name, {})
                                        if deliverable_data:
                                            sync_result = carton_sync.sync_deliverable_to_carton(
                                                project_id, feature_name, component_name, deliverable_name, deliverable_data
                                            )
                                            logger.info(f"Synced GIINT deliverable '{project_id}/{feature_name}/{component_name}/{deliverable_name}' to Carton")

                                elif sync_type == "sync_task":
                                    feature_name = arguments.get("feature_name")
                                    component_name = arguments.get("component_name")
                                    deliverable_name = arguments.get("deliverable_name")
                                    task_id = arguments.get("task_id")
                                    if feature_name and component_name and deliverable_name and task_id:
                                        feature_data = project.get("features", {}).get(feature_name, {})
                                        component_data = feature_data.get("components", {}).get(component_name, {})
                                        deliverable_data = component_data.get("deliverables", {}).get(deliverable_name, {})
                                        task_data = deliverable_data.get("tasks", {}).get(task_id, {})
                                        if task_data:
                                            sync_result = carton_sync.sync_task_to_carton(
                                                project_id, feature_name, component_name, deliverable_name, task_id, task_data
                                            )
                                            logger.info(f"Synced GIINT task '{project_id}/{feature_name}/{component_name}/{deliverable_name}/{task_id}' to Carton")

                        except Exception as e:
                            logger.error(f"GIINT-Carton sync failed for {project_id} (non-critical): {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"GIINT-Carton sync import/execution failed (non-critical): {e}", exc_info=True)

        # GIINT-TreeKanban sync hooks - push deliverables and tasks to TreeKanban
        with open('/tmp/omnisanc_giint_treekanban_trace.log', 'a') as f:
            f.write(f"{datetime.now()} TRACE: GIINT_AVAILABLE={GIINT_AVAILABLE}, tool_name={tool_name}\n")
            f.flush()
        print(f"🔍 [GIINT-TreeKanban Hook] GIINT_AVAILABLE={GIINT_AVAILABLE}, tool_name={tool_name}", file=sys.stderr)
        logger.info(f"[GIINT-TreeKanban Hook] GIINT_AVAILABLE={GIINT_AVAILABLE}, tool_name={tool_name}")
        if GIINT_AVAILABLE:
            treekanban_tool_mappings = {
                "mcp__giint-llm-intelligence__planning__add_deliverable_to_component": "push_deliverable",
                "mcp__giint-llm-intelligence__planning__add_task_to_deliverable": "push_task",
            }

            logger.info(f"[GIINT-TreeKanban Hook] PostToolUse fired for tool: {tool_name}")
            if tool_name in treekanban_tool_mappings:
                logger.info(f"[GIINT-TreeKanban Hook] Tool matched! Push type: {treekanban_tool_mappings[tool_name]}")
                try:
                    # Import TreeKanban SQLite client
                    from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient

                    # Get board name from GIINT's Strata config
                    giint_env = get_strata_mcp_env("giint-llm-intelligence")
                    logger.info(f"[GIINT-TreeKanban Hook] giint_env result: {giint_env}")
                    board_name = giint_env.get("GIINT_TREEKANBAN_BOARD")
                    logger.info(f"[GIINT-TreeKanban Hook] board_name: {board_name}")

                    if not board_name:
                        logger.error("GIINT_TREEKANBAN_BOARD not set in Strata config, skipping TreeKanban sync")
                    else:
                        push_type = treekanban_tool_mappings[tool_name]
                        project_id = arguments.get("project_id")

                        if not project_id:
                            logger.warning("GIINT-TreeKanban sync skipped: no project_id in arguments")
                        else:
                            # Load project from GIINT registry
                            try:
                                project_data = giint_projects.get_project(project_id)
                                if not project_data.get("success"):
                                    logger.error(f"Failed to load GIINT project {project_id}")
                                else:
                                    project = project_data.get("project")
                                    client = HeavenBMLSQLiteClient()

                                    if push_type == "push_deliverable":
                                        feature_name = arguments.get("feature_name")
                                        component_name = arguments.get("component_name")
                                        deliverable_name = arguments.get("deliverable_name")

                                        if feature_name and component_name and deliverable_name:
                                            feature_data = project.get("features", {}).get(feature_name, {})
                                            component_data = feature_data.get("components", {}).get(component_name, {})
                                            deliverable_data = component_data.get("deliverables", {}).get(deliverable_name, {})

                                            if deliverable_data:
                                                tags = ["giint", project_id, "deliverable", deliverable_name]

                                                # Get next root priority for the deliverable
                                                all_cards = client.get_all_cards(board_name)
                                                root_priorities = [
                                                    int(c.get("priority"))
                                                    for c in all_cards
                                                    if c.get("priority") not in ["NA", "none", None]
                                                    and "." not in c.get("priority", "")
                                                ]
                                                next_priority = str(max(root_priorities) + 1) if root_priorities else "1"
                                                logger.info(f"Assigning deliverable priority: {next_priority}")

                                                # Create deliverable with correct priority via direct API call
                                                import urllib.request
                                                card_data = {
                                                    "board": board_name,
                                                    "title": deliverable_name,
                                                    "description": deliverable_data.get("description", ""),
                                                    "status": "backlog",
                                                    "priority": next_priority,
                                                    "tags": json.dumps(tags)
                                                }

                                                req = urllib.request.Request(
                                                    'http://heaven_chat_frontend:3003/api/sqlite/cards',
                                                    data=json.dumps(card_data).encode(),
                                                    headers={'Content-Type': 'application/json'},
                                                    method='POST'
                                                )

                                                with urllib.request.urlopen(req) as response:
                                                    card_result = json.loads(response.read())

                                                logger.info(f"Pushed GIINT deliverable '{deliverable_name}' with priority {next_priority}: {card_result}")

                                                # Check if deliverable has vendored OperadicFlows
                                                operadic_flow_ids = deliverable_data.get("operadic_flow_ids", [])
                                                if operadic_flow_ids:
                                                    logger.info(f"Deliverable has {len(operadic_flow_ids)} vendored OperadicFlows, creating pattern cards")
                                                    try:
                                                        from heaven_base.tools.registry_tool import registry_util_func

                                                        for flow_id in operadic_flow_ids:
                                                            # Get OperadicFlow from registry
                                                            flow_result = registry_util_func("get", registry_name="opera_operadic_flows", key=flow_id)

                                                            if "Value for key" in flow_result or "Key not found" in flow_result:
                                                                logger.warning(f"OperadicFlow {flow_id} not found in registry, skipping")
                                                                continue

                                                            # Parse the flow data
                                                            import ast
                                                            start_idx = flow_result.find("{")
                                                            if start_idx != -1:
                                                                flow_data = ast.literal_eval(flow_result[start_idx:])
                                                                sequence = flow_data.get("sequence", [])
                                                                flow_name = flow_data.get("name", flow_id)

                                                                # Build description showing the pattern
                                                                description_parts = [
                                                                    f"**OperadicFlow Pattern**: {flow_name}",
                                                                    "",
                                                                    "**Sequence**:"
                                                                ]
                                                                for step_idx, step in enumerate(sequence):
                                                                    step_line = f"{step_idx + 1}. {step.get('item_type', 'Unknown')} - {step.get('description', 'No description')}"
                                                                    description_parts.append(step_line)
                                                                    if step.get('mission_type'):
                                                                        description_parts.append(f"   Mission: {step['mission_type']}")
                                                                    if step.get('human_capability'):
                                                                        description_parts.append(f"   Human: {step['human_capability']}")

                                                                pattern_description = "\n".join(description_parts)
                                                                pattern_tags = ["giint", project_id, "operadic_flow", flow_id]

                                                                flow_card_result = client.create_card(
                                                                    board=board_name,
                                                                    title=f"🔄 {flow_name}",
                                                                    description=pattern_description,
                                                                    lane="backlog",
                                                                    tags=pattern_tags
                                                                )
                                                                logger.info(f"Created OperadicFlow pattern card: {flow_name}")

                                                    except Exception as e:
                                                        logger.error(f"Failed to spawn OperadicFlow cards: {e}", exc_info=True)

                                    elif push_type == "push_task":
                                        feature_name = arguments.get("feature_name")
                                        component_name = arguments.get("component_name")
                                        deliverable_name = arguments.get("deliverable_name")
                                        task_id = arguments.get("task_id")

                                        if feature_name and component_name and deliverable_name and task_id:
                                            feature_data = project.get("features", {}).get(feature_name, {})
                                            component_data = feature_data.get("components", {}).get(component_name, {})
                                            deliverable_data = component_data.get("deliverables", {}).get(deliverable_name, {})
                                            task_data = deliverable_data.get("tasks", {}).get(task_id, {})

                                            if task_data:
                                                import urllib.request
                                                tags = ["giint", project_id, "deliverable", deliverable_name, "task", task_id]

                                                # Find deliverable card and existing children to calculate priority
                                                all_cards = client.get_all_cards(board_name)
                                                parent_card = None
                                                child_count = 0

                                                for card in all_cards:
                                                    card_tags_str = card.get("tags", "[]")
                                                    if isinstance(card_tags_str, str):
                                                        card_tags = json.loads(card_tags_str)
                                                    else:
                                                        card_tags = card_tags_str

                                                    # Check if card belongs to our deliverable
                                                    if (deliverable_name in card_tags and
                                                        "giint" in card_tags and
                                                        project_id in card_tags):
                                                        if "task" not in card_tags:
                                                            parent_card = card
                                                        else:
                                                            child_count += 1

                                                if not parent_card:
                                                    logger.error(f"Could not find deliverable card for {deliverable_name}")
                                                elif parent_card.get("priority", "NA") == "NA":
                                                    logger.error(f"Deliverable {deliverable_name} has no priority assigned")
                                                else:
                                                    # Calculate task priority as parent.N where N is child index
                                                    parent_priority = parent_card.get("priority")
                                                    task_priority = f"{parent_priority}.{child_count + 1}"
                                                    logger.info(f"Assigning task priority: {task_priority}")

                                                    # Create task with correct priority via direct API call
                                                    card_data = {
                                                        "board": board_name,
                                                        "title": task_data.get("description", task_id),
                                                        "description": task_data.get("details", ""),
                                                        "status": "backlog",
                                                        "priority": task_priority,
                                                        "tags": json.dumps(tags)
                                                    }

                                                    req = urllib.request.Request(
                                                        'http://heaven_chat_frontend:3003/api/sqlite/cards',
                                                        data=json.dumps(card_data).encode(),
                                                        headers={'Content-Type': 'application/json'},
                                                        method='POST'
                                                    )

                                                    with urllib.request.urlopen(req) as response:
                                                        card_result = json.loads(response.read())

                                                    logger.info(f"Pushed GIINT task '{task_id}' with priority {task_priority}: {card_result}")

                            except Exception as e:
                                logger.error(f"GIINT-TreeKanban sync failed for {project_id} (non-critical): {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"GIINT-TreeKanban sync import/execution failed (non-critical): {e}", exc_info=True)

        # OPERA-TreeKanban sync hook - spawn OperadicFlow cards when vendored
        if tool_name == "mcp__opera__vendor_operadic_flow":
            logger.info(f"[OPERA-TreeKanban Hook] vendor_operadic_flow detected")
            try:
                from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient
                from heaven_base.tools.registry_tool import registry_util_func
                import ast

                # Get board name from GIINT's Strata config
                giint_env = get_strata_mcp_env("giint-llm-intelligence")
                board_name = giint_env.get("GIINT_TREEKANBAN_BOARD")

                if not board_name:
                    logger.error("GIINT_TREEKANBAN_BOARD not set in Strata config, skipping OPERA-TreeKanban sync")
                else:
                    # Arguments are already unwrapped
                    project_id = arguments.get("project_id")
                    operadic_flow_id = arguments.get("operadic_flow_id")

                    if project_id and operadic_flow_id:
                        # Get OperadicFlow from registry
                        flow_result = registry_util_func("get", registry_name="opera_operadic_flows", key=operadic_flow_id)

                        if "Value for key" not in flow_result and "Key not found" not in flow_result:
                            # Parse the flow data
                            start_idx = flow_result.find("{")
                            if start_idx != -1:
                                flow_data = ast.literal_eval(flow_result[start_idx:])
                                sequence = flow_data.get("sequence", [])
                                flow_name = flow_data.get("name", operadic_flow_id)

                                # Build description showing the pattern
                                description_parts = [
                                    f"**OperadicFlow Pattern**: {flow_name}",
                                    "",
                                    "**Sequence**:"
                                ]
                                for step_idx, step in enumerate(sequence):
                                    step_line = f"{step_idx + 1}. {step.get('item_type', 'Unknown')} - {step.get('description', 'No description')}"
                                    description_parts.append(step_line)
                                    if step.get('mission_type'):
                                        description_parts.append(f"   Mission: {step['mission_type']}")
                                    if step.get('human_capability'):
                                        description_parts.append(f"   Human: {step['human_capability']}")

                                pattern_description = "\n".join(description_parts)
                                pattern_tags = ["giint", project_id, "operadic_flow", operadic_flow_id]

                                client = HeavenBMLSQLiteClient()
                                flow_card_result = client.create_card(
                                    board=board_name,
                                    title=flow_name,
                                    description=pattern_description,
                                    lane="backlog",
                                    tags=pattern_tags
                            )
                            logger.info(f"[OPERA-TreeKanban Hook] Created OperadicFlow pattern card: {flow_name}")

            except Exception as e:
                logger.error(f"OPERA-TreeKanban sync failed (non-critical): {e}", exc_info=True)

        # Auto-vendor default OperadicFlow when deliverable is auto-ratcheted
        if tool_name == "mcp__giint-llm-intelligence__get_next_task_from_treekanban":
            logger.info(f"[Auto-Vendor Hook] get_next_task_from_treekanban detected")

            try:
                # Check if result contains a deliverable card that was auto-ratcheted
                if isinstance(result, str):
                    result_data = json.loads(result)
                elif isinstance(result, list) and len(result) > 0:
                    # Strata wraps response in a list with content blocks: [{'type': 'text', 'text': '{...}'}]
                    text_content = result[0].get("text")
                    if text_content:
                        result_data = json.loads(text_content)
                    else:
                        result_data = None
                else:
                    result_data = result

                if result_data and result_data.get("success") and result_data.get("card"):
                    card = result_data["card"]
                    tags = card.get("tags", [])

                    # Check if it's a deliverable with no operadic_flow tag
                    is_deliverable = "deliverable" in tags and "task" not in tags
                    has_operadic_flow = "operadic_flow" in tags

                    if is_deliverable and not has_operadic_flow and GIINT_AVAILABLE:
                        logger.info(f"[Auto-Vendor Hook] Deliverable without OperadicFlow detected, auto-vendoring default")

                        # Extract project_id from tags (second element after "giint")
                        if "giint" in tags and len(tags) > tags.index("giint") + 1:
                            project_id = tags[tags.index("giint") + 1]
                            default_flow_id = "default_human_ai_collaboration"

                            # Get board name from GIINT's Strata config
                            giint_env = get_strata_mcp_env("giint-llm-intelligence")
                            board_name = giint_env.get("GIINT_TREEKANBAN_BOARD")

                            if board_name:
                                # Get OperadicFlow from registry and create pattern card (reusing OPERA-TreeKanban hook logic)
                                from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient
                                from heaven_base.tools.registry_tool import registry_util_func
                                import ast

                                flow_result = registry_util_func("get", registry_name="opera_operadic_flows", key=default_flow_id)

                                if "Value for key" not in flow_result and "Key not found" not in flow_result:
                                    # Parse the flow data
                                    start_idx = flow_result.find("{")
                                    if start_idx != -1:
                                        flow_data = ast.literal_eval(flow_result[start_idx:])
                                        sequence = flow_data.get("sequence", [])
                                        flow_name = flow_data.get("name", default_flow_id)

                                        # Build description showing the pattern
                                        description_parts = [
                                            f"**OperadicFlow Pattern**: {flow_name}",
                                            "",
                                            "**Sequence**:"
                                        ]
                                        for step_idx, step in enumerate(sequence):
                                            step_line = f"{step_idx + 1}. {step.get('item_type', 'Unknown')} - {step.get('description', 'No description')}"
                                            description_parts.append(step_line)
                                            if step.get('mission_type'):
                                                description_parts.append(f"   Mission: {step['mission_type']}")
                                            if step.get('human_capability'):
                                                description_parts.append(f"   Human: {step['human_capability']}")

                                        pattern_description = "\n".join(description_parts)
                                        pattern_tags = ["giint", project_id, "operadic_flow", default_flow_id]

                                        client = HeavenBMLSQLiteClient()
                                        deliverable_id = card.get("id")
                                        deliverable_priority = card.get("priority")
                                        deliverable_lane = card.get("lane", "build")

                                        # Get deliverable's children using get_family
                                        family = client.get_family(board=board_name, card_id=deliverable_id)
                                        existing_children = family.get("children", [])

                                        if not existing_children:
                                            logger.warning(f"[Auto-Vendor Hook] No existing children found for deliverable {deliverable_id}, skipping auto-vendor")
                                        else:
                                            logger.info(f"[Auto-Vendor Hook] Found {len(existing_children)} existing children, inserting pattern card")

                                            # Create pattern card with NA priority (using client.create_card)
                                            pattern_card_result = client.create_card(
                                                board=board_name,
                                                title=flow_name,
                                                description=pattern_description,
                                                lane=deliverable_lane,
                                                tags=pattern_tags
                                            )

                                            if not pattern_card_result:
                                                logger.error(f"[Auto-Vendor Hook] Failed to create pattern card")
                                            else:
                                                pattern_card_id = pattern_card_result.get("id")
                                                logger.info(f"[Auto-Vendor Hook] Created pattern card {pattern_card_id} with NA priority")

                                                # Move pattern card below deliverable (makes it first child)
                                                client.move_card_below(
                                                    board=board_name,
                                                    card_id=pattern_card_id,
                                                    target_id=deliverable_id
                                                )
                                                logger.info(f"[Auto-Vendor Hook] Moved pattern card {pattern_card_id} below deliverable {deliverable_id}")

                                                # Move all existing children below pattern card (makes them children of pattern card)
                                                for child in existing_children:
                                                    child_id = child.get("id")
                                                    client.move_card_below(
                                                        board=board_name,
                                                        card_id=child_id,
                                                        target_id=pattern_card_id
                                                    )
                                                    logger.info(f"[Auto-Vendor Hook] Moved child {child_id} below pattern card {pattern_card_id}")

                                                # Tag the deliverable card with "operadic_flow"
                                                if "operadic_flow" not in tags:
                                                    client.add_tag(board=board_name, card_id=deliverable_id, tag="operadic_flow")
                                                    logger.info(f"[Auto-Vendor Hook] Tagged deliverable {deliverable_id} with 'operadic_flow'")
                                else:
                                    logger.warning(f"[Auto-Vendor Hook] OperadicFlow {default_flow_id} not found in registry")
                            else:
                                logger.error("[Auto-Vendor Hook] GIINT_TREEKANBAN_BOARD not set, cannot create pattern card")

            except Exception as e:
                logger.error(f"Auto-vendor hook failed (non-critical): {e}", exc_info=True)

        return {"success": True}
        
    except Exception as e:
        logger.error(f"PostToolUseHook error: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Trace at VERY start
    with open('/tmp/omnisanc_entry.log', 'a') as f:
        f.write(f"{datetime.now()} HOOK ENTRY\n")
        f.flush()

    try:
        # Import strata unwrap helper
        from strata_unwrap import get_actual_tool_name, get_actual_tool_input

        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Trace RAW input before unwrapping
        with open('/tmp/omnisanc_raw_input.log', 'a') as f:
            f.write(f"{datetime.now()} RAW: tool={input_data.get('tool_name')}, has_tool_response={'tool_response' in input_data}\n")
            f.flush()

        # Unwrap Strata calls to get actual tool name and input
        tool_name = get_actual_tool_name(input_data)
        arguments = get_actual_tool_input(input_data)

        # Debug trace - write BEFORE the if check
        with open('/tmp/omnisanc_before_if.log', 'a') as f:
            f.write(f"{datetime.now()} tool_name={tool_name}, has_tool_response={'tool_response' in input_data}\n")
            f.flush()

        # Check if this is a PostToolUse hook (has tool_response field)
        if "tool_response" in input_data:
            # PostToolUse hook - call on_tool_result
            with open('/tmp/omnisanc_POSTTOOLUSE_SUCCESS.log', 'a') as f:
                f.write(f"{datetime.now()} PostToolUse! tool_name={tool_name}\n")
                f.flush()
            tool_result = input_data.get("tool_response")
            result = on_tool_result(tool_name, arguments, tool_result)
            # PostToolUse hooks always succeed (no blocking)
            with open('/tmp/omnisanc_POSTTOOLUSE_COMPLETE.log', 'a') as f:
                f.write(f"{datetime.now()} Completed! tool_name={tool_name}\n")
                f.flush()
            sys.exit(0)
        else:
            # PreToolUse hook - call on_tool_use
            with open('/tmp/omnisanc_PRETOOLUSE.log', 'a') as f:
                f.write(f"{datetime.now()} PreToolUse tool_name={tool_name}\n")
                f.flush()
            result = on_tool_use(tool_name, arguments)

            # Follow Claude Code hook pattern
            if not result.get("allowed", True):
                error_msg = result.get("error_message", "OMNISANC Core blocked tool")
                print(f"🚫 {error_msg}", file=sys.stderr)
                sys.exit(2)
            else:
                reason = result.get("reason", "")
                if reason:
                    print(f"✅ {reason}", file=sys.stderr)
                sys.exit(0)

    except Exception as e:
        print(f"🚨 OMNISANC Core error: {e}", file=sys.stderr)
        sys.exit(1)
