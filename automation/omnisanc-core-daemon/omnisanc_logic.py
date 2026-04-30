#!/usr/bin/env python3
"""
OMNISANC Logic - Core enforcement logic imported by daemon.

This module is loaded once by the daemon process. The kill switch
is handled by the daemon, not here.
"""
import os
import sys
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from datetime import datetime

# Set HEAVEN_DATA_DIR for registry access
os.environ["HEAVEN_DATA_DIR"] = "/tmp/heaven_data"

# Heaven registry for activity tracking and event logging
try:
    # PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
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

# Starlog module for JIT STARSYSTEM init (atomic with GIINT)
try:
    from starlog_mcp.starlog import Starlog
    STARLOG_AVAILABLE = True
except ImportError as e:
    with open('/tmp/omnisanc_starlog_import_error.log', 'w') as f:
        f.write(f"Starlog import failed: {e}\n")
        import traceback
        f.write(traceback.format_exc())
    STARLOG_AVAILABLE = False


def _path_to_starsystem_concept(path: str) -> str:
    """Convert filesystem path to Starsystem CartON concept name.
    /tmp/turn-based-ai-game-bots-v7 -> Starsystem_Tmp_Turn_Based_Ai_Game_Bots_V7
    """
    # Strip leading slash, replace / and - with _, title case each part
    normalized = path.lstrip('/')
    normalized = normalized.replace('/', '_').replace('-', '_').replace(' ', '_')
    parts = normalized.split('_')
    titled = '_'.join(p.capitalize() for p in parts if p)
    return f'Starsystem_{titled}'


def get_giint_project_for_starlog(starlog_path: str):
    """Find GIINT project for this starsystem path via CartON graph.

    Converts path to Starsystem concept name, then queries PART_OF relationship.
    Returns full CartON concept name (e.g. 'Giint_Project_Turn_Based_Ai_Game_Bots_V7').
    """
    try:
        from carton_mcp.carton_utils import CartOnUtils
        import json as _json
        utils = CartOnUtils()
        starsystem_name = _path_to_starsystem_concept(starlog_path)
        result = utils.query_wiki_graph(
            "MATCH (g:Wiki)-[:PART_OF]->(s:Wiki {n: $ss}) "
            "WHERE g.n STARTS WITH 'Giint_Project_' "
            "RETURN g.n AS project_name LIMIT 1",
            {"ss": starsystem_name}
        )
        data = _json.loads(result) if isinstance(result, str) else result
        if data.get("success") and data.get("data"):
            return data["data"][0].get("project_name")
        return None
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to query CartON for GIINT project: {e}")
        return None


def has_ready_tasks(project_id: str) -> bool:
    """Check if GIINT project has a COMPLETE, NAMED hierarchy with a build-ready deliverable.

    Uses CartON MCP (via HTTP) to query the ontology — NOT direct Neo4j.
    The hierarchy must have:
    1. A GIINT_Project with a Feature that is NOT _Unnamed
    2. That Feature has a Component that is NOT _Unnamed
    3. That Component has a Deliverable that is NOT _Unnamed

    _Unnamed nodes are auto-created by the system to ensure inference works.
    They signal that the GIINT planning flight needs to EVOLVE them into real names.

    Returns True if ready. Returns False on error (fail CLOSED — planning needed if can't verify).
    """
    import logging
    import httpx
    log = logging.getLogger(__name__)

    # Accept full CartON concept name (from get_giint_project_for_starlog) or raw project ID
    if project_id.startswith("Giint_Project_"):
        project_concept = project_id
    else:
        norm_id = project_id.replace("-", "_").replace(" ", "_")
        project_concept = f"Giint_Project_{norm_id}"

    try:
        from carton_mcp.carton_utils import CartOnUtils
        utils = CartOnUtils()

        # Check: Full GIINT chain with NO _Unnamed nodes via HAS_PART relationships
        # CartON stores all GIINT hierarchy levels with HAS_PART, typed by name prefix
        query = (
            "MATCH (p:Wiki {n: $proj})-[:HAS_PART]->(f:Wiki)-[:HAS_PART]->(c:Wiki)-[:HAS_PART]->(d:Wiki) "
            "WHERE f.n STARTS WITH 'Giint_Feature_' "
            "AND c.n STARTS WITH 'Giint_Component_' "
            "AND d.n STARTS WITH 'Giint_Deliverable_' "
            "AND NOT f.n ENDS WITH '_Unnamed' "
            "AND NOT c.n ENDS WITH '_Unnamed' "
            "AND NOT d.n ENDS WITH '_Unnamed' "
            "RETURN count(d) > 0 AS ok, "
            "collect(DISTINCT f.n) AS features, "
            "collect(DISTINCT c.n) AS components, "
            "collect(DISTINCT d.n) AS deliverables"
        )
        result = utils.query_wiki_graph(query, {"proj": project_concept})

        if not result.get("success") or not result.get("data"):
            log.info(f"[has_ready_tasks] {project_concept} — query failed or no data")
            return False

        data = result["data"]
        first = data[0] if isinstance(data, list) and data else {}
        ok = first.get("ok", False)

        if not ok:
            # Check for _Unnamed nodes
            unnamed_query = (
                "MATCH (p:Wiki {n: $proj})-[:HAS_PART*1..4]->(n:Wiki) "
                "WHERE n.n ENDS WITH '_Unnamed' "
                "RETURN collect(n.n) AS unnamed"
            )
            unnamed_result = utils.query_wiki_graph(unnamed_query, {"proj": project_concept})
            if unnamed_result.get("success") and unnamed_result.get("data"):
                ud = unnamed_result["data"]
                unnamed_list = ud[0].get("unnamed", []) if isinstance(ud, list) and ud else []
                if unnamed_list:
                    log.info(f"[has_ready_tasks] {project_concept} has _Unnamed nodes needing evolution: {unnamed_list}")
                else:
                    log.info(f"[has_ready_tasks] {project_concept} missing Feature→Component→Deliverable chain")
            return False

        components = first.get('components', [])
        log.info(
            f"[has_ready_tasks] {project_concept} _Unnamed check passed — "
            f"features: {first.get('features', [])}, components: {components}, "
            f"deliverables: {first.get('deliverables', [])}"
        )

        # Stub readiness check: components with HAS_PATH must have valid stubs
        if components:
            try:
                from llm_intelligence.projects import check_stubs_ready
                stub_result = check_stubs_ready(components)
                if not stub_result.get("ready", True):
                    log.info(f"[has_ready_tasks] {project_concept} stubs NOT ready: {stub_result.get('details', '')}")
                    return False
                log.info(f"[has_ready_tasks] {project_concept} stubs OK: {stub_result.get('details', '')}")
            except ImportError:
                log.info(f"[has_ready_tasks] check_stubs_ready not available, skipping stub check")

        return True
    except Exception as e:
        log.warning(f"[has_ready_tasks] Query failed, failing CLOSED (planning needed): {e}")
        return False


def _check_giint_planning_gate(starlog_path: str, requested_config: str, state: dict) -> dict:
    """Check if GIINT planning gate should redirect to planning flight.

    Returns {"allowed": True} if allowed as-is, or redirect with modified tool_input.
    Also injects flights into active mission if applicable.
    """
    # Skip gate if already requesting planning flight
    if requested_config and "giint_project_planning" in requested_config:
        return {"allowed": True}

    # Skip if no starlog path
    if not starlog_path:
        return {"allowed": True}

    giint_project_id = get_giint_project_for_starlog(starlog_path)

    # No linked GIINT project - REDIRECT to planning (must create one)
    if not giint_project_id:
        import logging
        log = logging.getLogger(__name__)
        log.info(
            f"[GIINT Planning Gate] No GIINT project linked to {starlog_path} — "
            f"redirecting to planning flight to create one"
        )
        giint_project_id = "(none — needs creation)"
        # Fall through to redirect logic below

    # Has ready tasks - allow (only check if project exists)
    elif has_ready_tasks(giint_project_id):
        return {"allowed": True}

    # No ready tasks - AUTO-REDIRECT to planning flight
    import logging
    log = logging.getLogger(__name__)
    log.info(
        f"[GIINT Planning Gate] Redirecting '{requested_config}' → 'giint_project_planning_flight_config' "
        f"(no ready tasks in project {giint_project_id})"
    )

    # If there's an active mission, inject both flights into the sequence
    mission_msg = ""
    if state.get("mission_active") and state.get("mission_id"):
        mission_id = state["mission_id"]
        try:
            # Import mission module for direct manipulation
            from starsystem import mission as mission_module

            loaded_mission = mission_module.load_mission(mission_id)
            # Allow injection if mission exists and isn't in terminal state
            terminal_statuses = {"completed", "cancelled", "failed"}
            if loaded_mission and loaded_mission.status not in terminal_statuses:
                # Create planning session
                planning_session = mission_module.MissionSession(
                    project_path=starlog_path,
                    flight_config="giint_project_planning_flight_config",
                    status="pending",
                    notes=f"Auto-injected: GIINT planning gate (no ready tasks in {giint_project_id})"
                )

                # Check if original flight is already in the mission sequence
                # (template-driven missions already have all flights queued)
                original_already_queued = any(
                    s.flight_config == requested_config
                    for s in loaded_mission.session_sequence[loaded_mission.current_step:]
                )

                current_step = loaded_mission.current_step
                # Always insert planning flight before current step
                loaded_mission.session_sequence.insert(current_step, planning_session)

                if not original_already_queued:
                    # Manual/ad-hoc mission — also queue the original flight after planning
                    original_session = mission_module.MissionSession(
                        project_path=starlog_path,
                        flight_config=requested_config,
                        status="pending",
                        notes=f"Queued: Original requested flight (after planning)"
                    )
                    loaded_mission.session_sequence.insert(current_step + 1, original_session)

                # Save updated mission
                mission_module.save_mission(loaded_mission)

                mission_msg = f"""
Mission '{mission_id}' updated:
  - Step {current_step}: Planning flight (runs now)
  - Step {current_step + 1}: {requested_config} (runs after planning)"""

                log.info(f"[GIINT Planning Gate] Injected planning + original flight into mission {mission_id}")

        except Exception as e:
            log.warning(f"[GIINT Planning Gate] Failed to inject into mission: {e}")
            mission_msg = f"\n⚠️ Could not auto-queue original flight in mission: {e}"

    return {
        "allowed": False,
        "error_message": f"""🛑 GIINT hierarchy not ready. You cannot start '{requested_config}'.

No ready tasks in GIINT project '{giint_project_id}'.
{mission_msg}

You MUST run the planning flight first:
  execute_action.exec {{"server_name": "waypoint", "action_name": "start_waypoint_journey", "body_schema": {{"config_path": "giint_project_planning_flight_config", "starlog_path": "{starlog_path}"}}}}

Planning flight creates the GIINT hierarchy (Project → Feature → Component → Deliverable → Task).
Once you have tasks with is_ready=True, the build flight will be allowed."""
    }


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
# CONNECTS_TO: /tmp/heaven_data/omnisanc_core/.course_state (read/write) — also accessed by autopoiesis stop hook, CAVE hooks
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

def resolve_claude_task(task_id: str) -> dict:
    """Resolve Claude Code task ID to full task data from disk.

    Claude Code stores tasks at ~/.claude/tasks/{session-id}/{task-number}.json.
    TaskUpdate only provides taskId, not subject — this reads it from disk.

    Returns:
        dict with task data (subject, description, status, metadata, etc.) or empty dict if not found.
    """
    import glob as glob_mod
    tasks_dir = os.path.expanduser("~/.claude/tasks")
    if not os.path.isdir(tasks_dir):
        return {}
    # Search all session directories for matching task ID
    pattern = os.path.join(tasks_dir, "*", f"{task_id}.json")
    matches = glob_mod.glob(pattern)
    if not matches:
        return {}
    # Use most recently modified if multiple matches
    target = max(matches, key=os.path.getmtime) if len(matches) > 1 else matches[0]
    try:
        with open(target, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[resolve_claude_task] Failed to read {target}: {e}")
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
                "giint_respond_called": False,  # NEW: LANDING step 3
                "jit_starlog_initialized": False  # NEW: JIT STARSYSTEM init flag
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
            # Ensure JIT starlog init flag exists for old state files
            if "jit_starlog_initialized" not in state:
                state["jit_starlog_initialized"] = False
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

def _derive_omnisanc_zone(state: dict) -> tuple:
    """Derive OMNISANC zone from state fields. Returns (state_name, zone_name, allowed_actions, next_step)."""
    course_plotted = state.get("course_plotted", False)
    mission_active = state.get("mission_active", False)
    session_active = state.get("session_active", False)
    needs_review = state.get("needs_review", False)

    if not course_plotted:
        return ("HOME", "CF_HOME",
                ["plot_course", "orient", "fly", "mission_create", "mission_select_menu", "get_health", "CartON tools"],
                "Plot a course: execute_action.exec {\"server_name\": \"starship\", \"action_name\": \"plot_course\", \"body_schema\": {\"project_paths\": [\"<path>\"], \"description\": \"<desc>\", \"domain\": \"starsystem\"}}")

    if needs_review:
        landing_step = 1
        if state.get("landing_routine_called", False):
            landing_step = 2
        if state.get("session_review_called", False):
            landing_step = 3
        return ("LANDING", "STARPORT_LANDING",
                ["landing_routine", "giint.respond", "orient", "CartON tools"],
                f"Complete landing step {landing_step}/3")

    if session_active:
        return ("JOURNEY", "STARSHIP_SESSION",
                ["ALL tools available", "update_debug_diary", "end_starlog"],
                "Work on your task. End with end_starlog when done.")

    # Check for active waypoint journey — if one exists, resume JOURNEY (not STARPORT)
    projects = state.get("projects", [])
    wp_state = _get_waypoint_state(projects)
    if wp_state and wp_state.get("status") not in (None, "END", "ABORTED"):
        project = projects[0] if projects else ""
        wp_flight = wp_state.get("config_filename", wp_state.get("config_path", "unknown"))
        wp_step = wp_state.get("completed_count", 0)
        wp_total = wp_state.get("total_waypoints", 0)
        wp_domain = wp_state.get("domain", "")
        wp_last_file = wp_state.get("last_served_file", "")
        # Restore session_active since waypoint journey is still running
        state["session_active"] = True
        save_course_state(state)
        return ("JOURNEY", "STARSHIP_SESSION",
                ["ALL tools available", "update_debug_diary", "end_starlog", "navigate_to_next_waypoint", "get_waypoint_progress", "abort_waypoint_journey"],
                f"RESUME: Active flight '{wp_flight}' (domain: {wp_domain}) at step {wp_step}/{wp_total}"
                f"{(' — last: ' + wp_last_file) if wp_last_file else ''}. "
                f"Use get_waypoint_progress to see current step content, then continue working or navigate_to_next_waypoint when ready.")

    # Course plotted, no session, no landing = STARPORT
    project = state.get("projects", [""])[0] if state.get("projects") else ""
    mission_id = state.get("mission_id", "none")
    return ("STARPORT", "STARPORT_LAUNCH",
            ["fly", "mission_create", "mission_select_menu", "mission_start", "start_waypoint_journey", "orient", "complete_mission", "mission_redo", "go_home"],
            f"Configure mission or start flight for {project}")


# CONNECTS_TO: /tmp/omnisanc_state.md (write) — also accessed by autopoiesis stop hook, CAVE hooks
OMNISANC_STATE_MD = "/tmp/omnisanc_state.md"

def _write_omnisanc_state_md(state: dict):
    """Write OMNISANC state as .md for MEMORY.md @include."""
    try:
        state_name, zone, allowed, next_step = _derive_omnisanc_zone(state)
        project = state.get("projects", [""])[0] if state.get("projects") else "none"
        mission_id = state.get("mission_id") or "none"
        mission_step = state.get("mission_step", 0)

        md = f"""## OMNISANC
STATE: {state_name} | ZONE: {zone}
PROJECT: {project}
MISSION: {mission_id} (step {mission_step})
ALLOWED: {', '.join(allowed)}
NEXT: {next_step}
"""
        with open(OMNISANC_STATE_MD, 'w') as f:
            f.write(md)
    except Exception as e:
        logger.error(f"Failed to write omnisanc_state.md: {e}")


def save_course_state(state: dict):
    """Save course state + project .md for MEMORY.md @include"""
    _ensure_course_dir()

    # Derive zone and persist it so other hooks can READ it without re-deriving
    try:
        state_name, zone, _, _ = _derive_omnisanc_zone(state)
        state["zone"] = state_name
    except Exception:
        pass

    try:
        with open(COURSE_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save course state: {e}")

    _write_omnisanc_state_md(state)

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

def _cleanup_waypoint_state(projects: list):
    """Remove waypoint state file to prevent stale state on next course."""
    if not projects:
        return
    project_path = projects[0] if isinstance(projects, list) else projects
    project_name = Path(project_path).name
    waypoint_file = f"/tmp/waypoint_state_{project_name}.json"
    try:
        if os.path.exists(waypoint_file):
            os.remove(waypoint_file)
            logger.info(f"Cleaned up waypoint state: {waypoint_file}")
    except Exception as e:
        logger.warning(f"Failed to clean up waypoint state {waypoint_file}: {e}")


# ──────────────────────────────────────────────────────────────
# Zone Screen Helpers — ONE source of truth for PreToolUse AND PostToolUse
# ──────────────────────────────────────────────────────────────

def _screen_home(state: dict) -> str:
    """Generate HOME zone screen."""
    project = state.get("projects", [""])[0] if state.get("projects") else ""
    path_placeholder = project if project else "<path>"
    return f"""🏰🌐
[🏠 HOME]: No active course. Welcome to Crystal Forest.

HOME OPTIONS:
1. Plot a course:
   execute_action.exec {{"server_name": "starship", "action_name": "plot_course", "body_schema": {{"project_paths": ["{path_placeholder}"], "description": "<desc>", "domain": "starsystem"}}}}

2. Orient:
   execute_action.exec {{"server_name": "starlog", "action_name": "orient", "body_schema": {{}}}}

3. Create a mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"mission_id": "<task-name>", "mission_type": "bml_default", "mission_type_domain": "odyssey", "variables": {{"project_path": "{path_placeholder}", "project_name": "<task-name>"}}}}}}

4. Select existing mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

5. Get next agent task from TK:
   execute_action.exec {{"server_name": "giint-llm-intelligence", "action_name": "get_next_task_from_treekanban", "body_schema": {{"agent_tasks_only": true}}}}"""


def _screen_starport(state: dict) -> str:
    """Generate STARPORT zone screen."""
    project = state.get("projects", [""])[0] if state.get("projects") else ""
    mission_id = state.get("mission_id")

    step, total, flight = 0, 0, None
    if mission_id:
        try:
            from starsystem.mission import load_mission as _lm_screen
            m = _lm_screen(mission_id)
            if m:
                step = m.current_step
                total = len(m.session_sequence)
                flight = m.session_sequence[step].flight_config if step < total else None
        except Exception:
            pass

    is_empty = total == 0 or flight is None

    if not mission_id or is_empty:
        return f"""🏰🌐
[🎯 STARPORT]: Course plotted — select what to run.
Project: {project}

🔮 PREDICT FIRST: Ask Flight Predictor what you need:
  execute_action.exec {{"server_name": "flight-predictor", "action_name": "scry_crystal_ball", "body_schema": {{"steps": [{{"step_number": 1, "description": "<what you want to do>"}}]}}}}

FP serves the HIGHEST available assembly — operadics > missions > flights > skill clusters.
If prediction is good, confirm it. If not, manual select below (your correction improves FP).

Browse STARPORT skills (top level = goldenized operadic flows):
  ls /tmp/heaven_data/system_starsystems/starport/.claude/skills/

If no operadics yet, drop to missions:
  ls /tmp/heaven_data/system_starsystems/starport/missions/.claude/skills/

If you REALLY need a raw flight:
  ls /tmp/heaven_data/system_starsystems/starport/flights/.claude/skills/

Each skill IS a menu item. Read its SKILL.md for exact commands."""
    else:
        return f"""🏰🌐
[🎯 MISSION STARPORT]: Mission '{mission_id}' — step {step + 1}/{total}

Next flight: {flight}
Project: {project}

🔮 PREDICT: Ask Flight Predictor if this is the right approach:
   execute_action.exec {{"server_name": "flight-predictor", "action_name": "scry_crystal_ball", "body_schema": {{"steps": [{{"step_number": 1, "description": "mission {mission_id} step {step + 1}: {flight}"}}]}}}}

STARPORT OPTIONS:
1. Start the mission's next flight:
   execute_action.exec {{"server_name": "waypoint", "action_name": "start_waypoint_journey", "body_schema": {{"config_path": "{flight}", "starlog_path": "{project}"}}}}

2. Browse available flights:
   execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project}"}}}}

3. Create a different mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"mission_id": "<id>", "name": "<name>", "description": "<desc>"}}}}

4. Select existing mission type:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

5. Check mission status:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_get_status", "body_schema": {{"mission_id": "{mission_id}"}}}}

6. Complete current mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "complete_mission", "body_schema": {{"mission_id": "{mission_id}"}}}}

7. Extract from mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_request_extraction", "body_schema": {{"mission_id": "{mission_id}"}}}}

8. Redo mission (reset to BUILD):
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_redo", "body_schema": {{"mission_id": "{mission_id}", "notes": "reason for redo"}}}}"""


def _screen_landing(state: dict) -> str:
    """Generate LANDING zone screen for current step."""
    landing_done = state.get("landing_routine_called", False)
    review_done = state.get("session_review_called", False)
    qa_id = state.get("qa_id", "UNKNOWN")
    project_path = state.get("projects", ["unknown"])[0] if state.get("projects") else "unknown"

    if not landing_done:
        return f"""🛬 LANDING Step 1 of 3. Run landing_routine:
  execute_action.exec {{"server_name": "starship", "action_name": "landing_routine", "body_schema": {{"starlog_path": "{project_path}"}}}}
Then: session_review → core__respond"""
    elif not review_done:
        return f"""🛬 LANDING Step 2 of 3. ✅ Step 1 done. Run session_review:
  execute_action.exec {{"server_name": "starship", "action_name": "session_review", "body_schema": {{"starlog_path": "{project_path}", "got_compacted": false}}}}
Then: core__respond"""
    else:
        return f"""🛬 LANDING Step 3 of 3. ✅ Steps 1-2 done. Run core__respond:
  execute_action.exec {{"server_name": "giint-llm-intelligence", "action_name": "core__respond", "body_schema": {{"qa_id": "{qa_id}", "user_prompt_description": "<summary of what you did this session>", "one_liner": "<one sentence summary>", "key_tags": "<relevant tags list>", "involved_files": "<files you touched list>", "project_path": "{project_path}", "feature": "<GIINT_Feature you worked on>", "component": "<GIINT_Component you modified>", "deliverable": "<GIINT_Deliverable you produced>", "subtask": "<specific subtask if any>", "task": "<GIINT_Task name>", "workflow_id": "{qa_id}"}}}}
This is the final step before returning to STARPORT."""


def _screen_journey(state: dict) -> str:
    """Generate JOURNEY/PLANETSIDE zone screen."""
    project = state.get("projects", [""])[0] if state.get("projects") else ""
    return f"""🏰🌐
[🌍 JOURNEY]: Starlog session active — you're on the planet, working.
Project: {project}

SESSION OPTIONS:
1. Update debug diary:
   execute_action.exec {{"server_name": "starlog", "action_name": "update_debug_diary", "body_schema": {{"path": "{project}", "entry": {{"type": "insight", "content": "..."}}}}}}

2. Navigate to next waypoint:
   execute_action.exec {{"server_name": "waypoint", "action_name": "navigate_to_next_waypoint", "body_schema": {{}}}}

3. Check waypoint progress:
   execute_action.exec {{"server_name": "waypoint", "action_name": "get_waypoint_progress", "body_schema": {{"starlog_path": "{project}"}}}}

4. End session (when waypoint journey is at END):
   execute_action.exec {{"server_name": "starlog", "action_name": "end_starlog", "body_schema": {{"end_content": "...", "path": "{project}"}}}}

All tools are available during JOURNEY mode."""


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
# ALL ENTRIES MUST BE LOWERCASE — validate_home_mode uses tool_name.lower() for matching
HOME_MODE_TOOLS = {
    # HOME = lobby. Orient, talk to user, start a mission. NOTHING ELSE.
    # View-only (read, search — NO writes)
    "read",
    "glob",
    "grep",
    "bash",  # Validated separately: only cd, cat, ls, pwd — NO writes

    # Orient
    "mcp__starlog__orient",

    # Course management (HOME → STARPORT transition, or resume after compaction)
    "mcp__starship__plot_course",
    "mcp__starsystem__plot_course",  # starsystem-wrapped name via treeshell
    "mcp__starship__continue_course",
    "mcp__starsystem__continue_course",  # defensive: allow resume even if HOME shouldn't have compacted course
    "mcp__starsystem__mission_create",
    "mcp__starsystem__mission_start",
    "mcp__starsystem__mission_get_status",
    "mcp__starsystem__mission_list",
    "mcp__starsystem__mission_request_extraction",
    "mcp__starsystem__mission_redo",
    "mcp__starsystem__mission_select_menu",
    "mcp__starsystem__view_mission_config",
    "mcp__starsystem__create_mission_type",

    # OMNISANC control
    "mcp__starsystem__toggle_omnisanc",

    # TreeKanban — pull next task at HOME before plotting course
    # Strata unwrap drops core__ prefix: execute_action server=giint-llm-intelligence action=get_next_task_from_treekanban
    "mcp__giint-llm-intelligence__get_next_task_from_treekanban",
    "mcp__giint-llm-intelligence__core__get_next_task_from_treekanban",  # direct MCP name (if equipped without strata)

    # Carton knowledge graph (persistence is infrastructure)
    "mcp__carton__get_recent_concepts",
    "mcp__carton__query_wiki_graph",
    "mcp__carton__get_concept",
    "mcp__carton__get_concept_network",
    "mcp__carton__add_concept",
    "mcp__carton__add_observation_batch",
    "mcp__carton__observe_from_identity_pov",
    "mcp__carton__chroma_query",
    "mcp__carton__activate_collection",

    # OPERA pattern management (view-only)
    "mcp__opera__view_canopy_patterns",
    "mcp__opera__get_pattern_details",
    "mcp__opera__view_operadic_flows",

    # STARSYSTEM observability
    "mcp__starsystem__check_selfplay_logs",
    "mcp__starsystem__get_fitness_score",

    # Skills (context loading only — can't execute anything from HOME)
    "skill",
    "mcp__sancrev_treeshell__run_conversation_shell",

    # Task management
    "taskcreate",
    "taskupdate",
    "tasklist",
    "taskget",

    # Infrastructure — schema fetching for deferred MCP tools
    "toolsearch",
}

def is_base_mission(state: dict) -> bool:
    """
    Check if base mission (implicit mission) is active.

    Base mission = auto-created by STARSYSTEM when plot_course() is called
    without an explicit mission_create(). The mission_id starts with "base_mission_".

    Base missions are single-session containers. After end_starlog, user must
    re-plot course (enforced in PostToolUse handler).
    """
    mission_id = state.get("mission_id", "") or ""
    return (state.get("course_plotted", False) and
            mission_id.startswith("base_mission_") and
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

    # Allow infrastructure commands (not project-specific code execution)
    safe_commands = [
        "mkdir", "cd", "ls", "pwd", "cat", "head", "tail", "wc",
        "pip", "pip3",  # Package management
        "git",  # Version control
        "python", "python3",  # Testing/running scripts
        "curl", "wget",  # Network tools
        "echo", "date", "which", "env", "printenv",
        "cp", "mv",  # File operations
        "chmod",  # Permissions
        "self_compact", "self_restart",  # Self-management
        "touch", "diff",
        "gh",  # GitHub CLI
        "docker",  # Container management
    ]
    return any(command.startswith(cmd) for cmd in safe_commands)

def validate_home_mode(tool_name: str, arguments: dict) -> dict:
    """Validate tool usage in Home Mode (no course plotted)"""

    # Check if tool is allowed in Home Mode (case-insensitive for MCP tool names)
    if tool_name.lower() in HOME_MODE_TOOLS:
        # Special handling for Bash (compare lowered since we lowered tool_name above)
        if tool_name.lower() == "bash":
            if is_safe_bash_command(arguments):
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[🏠 HOME]: Bash command not in safe list. Allowed: mkdir, cd, ls, pwd, pip, git, python, curl, self_compact, self_restart, etc.
To enter Journey Mode:
  execute_action.exec {"server_name": "starship", "action_name": "plot_course", "body_schema": {"project_paths": ["<actual repo path>"], "description": "<what you are doing>", "domain": "<domain>"}}"""
                }
        return {"allowed": True}

    # Tool not allowed in Home Mode
    return {
        "allowed": False,
        "error_message": f"""🏰🌐
[🏠 HOME]: Tool '{tool_name}' not allowed in Home Mode. Use `jump cf_home` for HOME orientation, or:
execute_action.exec {{"server_name": "starship", "action_name": "plot_course", "body_schema": {{"project_path": "<path>", "description": "<desc>"}}}}"""
    }

def validate_journey_mode(tool_name: str, state: dict, arguments: dict = None) -> dict:
    """Validate tool usage in Journey Mode (course plotted)"""

    # ALWAYS allowed in ALL phases — never block these (case-insensitive for treeshell unwrap)
    ALWAYS_ALLOWED = {
        "mcp__starsystem__toggle_omnisanc",
    }
    if tool_name.lower() in ALWAYS_ALLOWED:
        return {"allowed": True}

    # Block extraction if session is active or waypoint journey in progress
    if tool_name.lower() == "mcp__starsystem__mission_request_extraction":
        if state.get("session_active", False):
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🛑 BLOCKED]: Cannot extract while session is active

You must end the session first (use these EXACT treeshell commands):
1. execute_action.exec {{"server_name": "starlog", "action_name": "end_starlog", "body_schema": {{"path": "<project_path>", "summary": "..."}}}}
2. execute_action.exec {{"server_name": "waypoint", "action_name": "abort_waypoint_journey", "body_schema": {{}}}}
3. execute_action.exec {{"server_name": "starsystem", "action_name": "mission_request_extraction", "body_schema": {{"mission_id": "..."}}}}

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
1. execute_action.exec {"server_name": "waypoint", "action_name": "abort_waypoint_journey", "body_schema": {}}
2. execute_action.exec {"server_name": "starsystem", "action_name": "mission_request_extraction", "body_schema": {"mission_id": "<your mission id>"}}

Then you can plot a new course if desired."""
            }

    # mission_create is allowed in STARPORT (fly_called=False gate handles it)
    # Only block mission_create if already in an active session (JOURNEY/PLANETSIDE)
    if tool_name.lower() == "mcp__starsystem__mission_create":
        if state.get("session_active", False):
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🛑 BLOCKED]: Cannot create missions during active session.

End your session first, then configure missions in STARPORT.

1. server=starlog, action=end_starlog (end current session)
2. Then create missions in STARPORT"""
            }

    # mission_start: ALLOW from STARPORT (course plotted) or if resuming active mission
    # BLOCK only during active SESSION (journey mode)
    if tool_name.lower() == "mcp__starsystem__mission_start":
        if state.get("session_active", False):
            return {
                "allowed": False,
                "error_message": """🏰🌐
[🛑 BLOCKED]: Cannot start a mission during active session.

End your session first:
1. server=starlog, action=end_starlog
2. Complete landing sequence
3. Then start mission from STARPORT"""
            }
        else:
            # Course plotted (STARPORT) or resuming — allow
            return {"allowed": True}

    # Check if continue_course was called - must call orient
    if state.get("continue_course_called", False):
        if tool_name == "mcp__starlog__orient":
            return {"allowed": True}
        # Infrastructure tools (CartON, Skill, Task, etc.) always allowed
        elif tool_name in HOME_MODE_TOOLS:
            if tool_name == "Bash":
                if is_safe_bash_command(arguments or {}):
                    return {"allowed": True}
            else:
                return {"allowed": True}
        else:
            project_path = state.get('projects', [''])[0] if state.get('projects') else ''
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🔄 JOURNEY]: Reorientation required after continue_course().

→ execute_action.exec {{"server_name": "starlog", "action_name": "orient", "body_schema": {{"path": "{project_path}"}}}}

This clears the compact flag and you continue from where you left off."""
            }

    # Check if course was compacted (conversation was compacted)
    if state.get("was_compacted", False):
        # Must either continue_course() or plot_course() (which overwrites)
        if tool_name == "mcp__starship__continue_course":
            return {"allowed": True}
        elif tool_name == "mcp__starship__plot_course":
            return {"allowed": True}
        # Infrastructure tools (CartON, Skill, Task, etc.) always allowed
        elif tool_name in HOME_MODE_TOOLS:
            if tool_name == "Bash":
                if is_safe_bash_command(arguments or {}):
                    return {"allowed": True}
            else:
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
Use these EXACT treeshell commands:
1. execute_action.exec {{"server_name": "starship", "action_name": "continue_course", "body_schema": {{}}}}
2. execute_action.exec {{"server_name": "starship", "action_name": "plot_course", "body_schema": {{"project_path": "<path>", "description": "<desc>"}}}}

Cannot use other tools until you continue or plot a new course."""
            }

    # Check if LANDING phase must complete (sequential 3-step enforcement)
    if state.get("needs_review", False):
        landing_done = state.get("landing_routine_called", False)
        review_done = state.get("session_review_called", False)
        giint_done = state.get("giint_respond_called", False)

        # Infrastructure tools allowed during ALL landing steps
        # (needed for e.g. connecting MCP servers before giint.respond)
        LANDING_INFRA_TOOLS = {
            "Read", "Glob", "Grep", "Bash", "Write", "Edit",
            "Skill", "skill",
            "mcp__sancrev_treeshell__run_conversation_shell",
            "mcp__carton__add_concept", "mcp__carton__get_concept",
            "mcp__carton__query_wiki_graph", "mcp__carton__chroma_query",
            "mcp__carton__add_observation_batch",
            "mcp__carton__get_concept_network",
            "mcp__starlog__update_debug_diary",
        }
        if tool_name in LANDING_INFRA_TOOLS:
            return {"allowed": True}

        # Step 1: Must call landing_routine first
        if not landing_done:
            if tool_name == "mcp__starship__landing_routine":
                return {"allowed": True}
            # Allow Canopy completion during LANDING Step 1
            elif tool_name in ["mcp__canopy__mark_complete", "mcp__canopy__update_item_status"]:
                return {"allowed": True}
            else:
                _proj = state.get('projects', [''])[0] if state.get('projects') else ''
                return {
                    "allowed": False,
                    "error_message": f"""🛑 You tried '{tool_name}'. Not allowed during LANDING step 1 of 3.
Session ended. Complete the 3-step LANDING sequence.

STEP 1 (NOW) — run landing_routine:
  execute_action.exec {{"server_name": "starship", "action_name": "landing_routine", "body_schema": {{"starlog_path": "{_proj}"}}}}

STEP 2 (after step 1): session_review
STEP 3 (after step 2): core__respond

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
                _proj = state.get('projects', [''])[0] if state.get('projects') else ''
                return {
                    "allowed": False,
                    "error_message": f"""🛑 You tried '{tool_name}'. Not allowed during LANDING step 2 of 3.
✅ Step 1 complete (landing_routine)

STEP 2 (NOW) — run session_review:
  execute_action.exec {{"server_name": "starship", "action_name": "session_review", "body_schema": {{"starlog_path": "{_proj}", "got_compacted": false}}}}

STEP 3 (after step 2): core__respond

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
                project_path = state.get("projects", ["unknown"])[0] if state.get("projects") else "unknown"
                domain = state.get("domain", "HOME")
                subdomain = state.get("subdomain", "unknown")

                return {
                    "allowed": False,
                    "error_message": f"""🛑 You tried '{tool_name}'. Not allowed during LANDING step 3 of 3.
✅ Step 1 complete (landing_routine)
✅ Step 2 complete (session_review)

STEP 3 (NOW) — run core__respond:
  execute_action.exec {{"server_name": "giint-llm-intelligence", "action_name": "core__respond", "body_schema": {{"qa_id": "{qa_id}", "user_prompt_description": "<summary of what you did this session>", "one_liner": "<one sentence summary>", "key_tags": "<relevant tags list>", "involved_files": "<files you touched list>", "project_path": "{project_path}", "feature": "mission_work", "component": "uncategorized", "deliverable": "session_intelligence", "subtask": "session_capture", "task": "capture", "workflow_id": "{qa_id}"}}}}

This is the final step before returning to STARPORT."""
                }

    # Check if mission is active and session just ended (mission enforcement)
    if (state.get("mission_active", False) and
        state.get("waypoint_step", 0) == 0 and
        not state.get("session_active", False) and
        state.get("flight_selected")):

        # Allow mission management tools + abort for extraction cleanup
        if tool_name.lower() in ["mcp__starsystem__mission_get_status",
                         "mcp__starsystem__mission_inject_step",
                         "mcp__starsystem__mission_request_extraction",
                         "mcp__starsystem__mission_redo",
                         "mcp__starsystem__complete_mission",
                         "mcp__starsystem-mcp__starsystem__complete_mission",
                         "mcp__waypoint__abort_waypoint_journey"
                        ]:
            return {"allowed": True}

        # Allow waypoint.start to continue mission (with flight sequence + is_ready enforcement)
        if tool_name == "mcp__waypoint__start_waypoint_journey":
            starlog_path = arguments.get("starlog_path", "")
            requested_config = arguments.get("flight_config_name", "") or arguments.get("config_path", "")

            # GATE 1: GIINT is_ready check — blocks and instructs to use planning flight
            gate_result = _check_giint_planning_gate(starlog_path, requested_config, state)
            if not gate_result.get("allowed", True):
                return gate_result

            # GATE 2: Flight sequence enforcement — requested flight must match mission step
            mission_id = state.get("mission_id")
            if mission_id:
                try:
                    loaded_mission = mission.load_mission(mission_id)
                    if loaded_mission and loaded_mission.current_step < len(loaded_mission.session_sequence):
                        expected_session = loaded_mission.session_sequence[loaded_mission.current_step]
                        expected_flight = expected_session.flight_config
                        # Normalize for comparison (strip path, compare names)
                        req_name = requested_config.replace(".json", "").split("/")[-1]
                        exp_name = expected_flight.replace(".json", "").split("/")[-1]
                        if req_name != exp_name:
                            return {
                                "allowed": False,
                                "error_message": f"""🏰🌐
[🚫 FLIGHT SEQUENCE]: Wrong flight for current mission step.

Mission: {mission_id}
Current step: {loaded_mission.current_step + 1}/{len(loaded_mission.session_sequence)}
Expected flight: {expected_flight}
Requested flight: {requested_config}

You must start the correct flight for this mission step.
Use mission_get_status to see the full sequence."""
                            }
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Flight sequence check failed: {e}")
                    # Fail open — don't block on check errors

            # Both gates passed — return planning gate result (may have redirect)
            return gate_result

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
        project = state.get("projects", [""])[0] if state.get("projects") else ""
        # Read current flight from mission
        try:
            from starsystem.mission import load_mission as _load_m
            _m = _load_m(mission_id)
            _step = _m.current_step if _m else 0
            _total = len(_m.session_sequence) if _m else 0
            _flight = _m.session_sequence[_step].flight_config if _m and _step < _total else None
        except Exception:
            _step, _total, _flight = 0, 0, None

        # Branch display: empty base_mission vs real mission with flights
        is_empty_base = _total == 0 or _flight is None
        if is_empty_base:
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🎯 MISSION STARPORT]: Tool '{tool_name}' not allowed at this phase.
Allowed tools: start_waypoint_journey, fly, orient, mission_create, mission_start, mission_select_menu, toggle_omnisanc, go_home, get_course_state, Skill, Read, Glob, Grep, Task*
Project: {project}

You need to CREATE or SELECT a mission before you can work.
Use /bml-mission-loop-e2e skill to start a BML mission for your current task.

STARPORT OPTIONS:
1. Create a BML mission (RECOMMENDED — use skill /bml-mission-loop-e2e):
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"mission_id": "<task-name>", "mission_type": "bml_default", "mission_type_domain": "odyssey", "variables": {{"project_path": "{project}", "project_name": "<task-name>"}}}}}}

2. Browse available flights first:
   execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project}"}}}}

3. Select from existing mission types:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

4. Scry Crystal Ball for recommendations:
   execute_action.exec {{"server_name": "crystal-ball", "action_name": "scry", "body_schema": {{}}}}"""
            }
        else:
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🎯 MISSION STARPORT]: Mission '{mission_id}' — step {_step + 1}/{_total}

Next flight: {_flight}
Project: {project}

STARPORT OPTIONS:
1. Start the mission's next flight:
   execute_action.exec {{"server_name": "waypoint", "action_name": "start_waypoint_journey", "body_schema": {{"config_path": "{_flight}", "starlog_path": "{project}"}}}}

2. Browse available flights:
   execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project}"}}}}

3. Create a different mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"mission_id": "<id>", "name": "<name>", "description": "<desc>"}}}}

4. Select existing mission type:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

5. Check mission status:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_get_status", "body_schema": {{"mission_id": "{mission_id}"}}}}

6. Complete current mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "complete_mission", "body_schema": {{"mission_id": "{mission_id}"}}}}

7. Extract from mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_request_extraction", "body_schema": {{"mission_id": "{mission_id}"}}}}"""
            }

    # MISSION MODE: Skip fly() requirement — mission drives flight selection
    if state.get("mission_active") and not state.get("fly_called", False):
        mission_id = state.get("mission_id", "unknown")
        # Allow waypoint start (mission's flight), mission management, and toggle
        if tool_name == "mcp__waypoint__start_waypoint_journey":
            starlog_path = arguments.get("starlog_path", "")
            requested_config = arguments.get("flight_config_name", "") or arguments.get("config_path", "")

            # GATE 1: GIINT is_ready check — blocks and instructs to use planning flight
            gate_result = _check_giint_planning_gate(starlog_path, requested_config, state)
            if not gate_result.get("allowed", True):
                return gate_result

            # GATE 2: Flight sequence enforcement — requested flight must match mission step
            if mission_id and mission_id != "unknown":
                try:
                    loaded_mission = mission.load_mission(mission_id)
                    if loaded_mission and loaded_mission.current_step < len(loaded_mission.session_sequence):
                        expected_session = loaded_mission.session_sequence[loaded_mission.current_step]
                        expected_flight = expected_session.flight_config
                        req_name = requested_config.replace(".json", "").split("/")[-1]
                        exp_name = expected_flight.replace(".json", "").split("/")[-1]
                        if req_name != exp_name:
                            return {
                                "allowed": False,
                                "error_message": f"""🏰🌐
[🚫 FLIGHT SEQUENCE]: Wrong flight for current mission step.

Mission: {mission_id}
Current step: {loaded_mission.current_step + 1}/{len(loaded_mission.session_sequence)}
Expected flight: {expected_flight}
Requested flight: {requested_config}

You must start the correct flight for this mission step.
Use mission_get_status to see the full sequence."""
                            }
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Flight sequence check failed: {e}")

            return gate_result
        if tool_name.lower() in {"mcp__starsystem__toggle_omnisanc", "mcp__starsystem__mission_get_status",
                                  "mcp__starsystem__mission_request_extraction", "mcp__starsystem__mission_report_progress",
                                  "mcp__starsystem__mission_inject_step", "mcp__starsystem__complete_mission",
                                  "mcp__starsystem__mission_redo",
                                  "mcp__starsystem-mcp__starsystem__complete_mission",
                                  "mcp__starsystem__mission_create", "mcp__starsystem__mission_select_menu",
                                  "mcp__starsystem__mission_start",
                                  "mcp__starlog__orient",
                                  "mcp__starship__fly",
                                  "mcp__starship__get_course_state",
                                  "skill", "mcp__sancrev_treeshell__run_conversation_shell",
                                  "mcp__starship__launch_routine",
                                  "mcp__starsystem__go_home",
                                  "read", "glob", "grep",
                                  "task",
                                  "taskcreate", "taskupdate", "tasklist", "taskget"}:
            return {"allowed": True}
        # Block everything else with mission-aware instructions
        project = state.get('projects', [''])[0] if state.get('projects') else ''
        # Read current flight from mission
        try:
            from starsystem.mission import load_mission
            m = load_mission(mission_id)
            step = m.current_step if m else 0
            total = len(m.session_sequence) if m else 0
            flight = m.session_sequence[step].flight_config if m and step < total else None
        except Exception:
            step, total, flight = 0, 0, None

        is_empty = total == 0 or flight is None
        if is_empty:
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🎯 MISSION STARPORT]: Tool '{tool_name}' not allowed at this phase.
Allowed tools: start_waypoint_journey, fly, orient, mission_create, mission_start, mission_select_menu, toggle_omnisanc, go_home, get_course_state, launch_routine, Skill, Read, Glob, Grep, Task*
Project: {project}

You need to CREATE or SELECT a mission before you can work.
Use /bml-mission-loop-e2e skill to start a BML mission for your current task.

STARPORT OPTIONS:
1. Create a BML mission (RECOMMENDED — use skill /bml-mission-loop-e2e):
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"mission_id": "<task-name>", "mission_type": "bml_default", "mission_type_domain": "odyssey", "variables": {{"project_path": "{project}", "project_name": "<task-name>"}}}}}}

2. Browse available flights first:
   execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project}"}}}}

3. Select from existing mission types:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

4. Scry Crystal Ball for recommendations:
   execute_action.exec {{"server_name": "crystal-ball", "action_name": "scry", "body_schema": {{}}}}"""
            }
        else:
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🎯 MISSION STARPORT]: Mission '{mission_id}' — step {step + 1}/{total}

Next flight: {flight}
Project: {project}

🔮 PREDICT: Ask Flight Predictor if this is the right approach:
   execute_action.exec {{"server_name": "flight-predictor", "action_name": "scry_crystal_ball", "body_schema": {{"steps": [{{"step_number": 1, "description": "mission {mission_id} step {step + 1}: {flight}"}}]}}}}

STARPORT OPTIONS:
1. Start the mission's next flight:
   execute_action.exec {{"server_name": "waypoint", "action_name": "start_waypoint_journey", "body_schema": {{"config_path": "{flight}", "starlog_path": "{project}"}}}}

2. Browse available flights:
   execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project}"}}}}

3. Create a different mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"mission_id": "<id>", "name": "<name>", "description": "<desc>"}}}}

4. Select existing mission type:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

5. Check mission status:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_get_status", "body_schema": {{"mission_id": "{mission_id}"}}}}

6. Complete current mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "complete_mission", "body_schema": {{"mission_id": "{mission_id}"}}}}"""
            }

    # Check if fly has been called (enables waypoint.start) — NON-MISSION path
    if not state.get("fly_called", False):
        # STARPORT allowed tools: fly, launch, mission config, toggle, course state
        if tool_name in ["mcp__starship__fly", "mcp__starship__launch_routine"]:
            return {"allowed": True}
        elif tool_name.lower() in {"mcp__starsystem__mission_create", "mcp__starsystem__mission_select_menu",
                                    "mcp__starsystem__mission_start", "mcp__starsystem__toggle_omnisanc",
                                    "mcp__starsystem__mission_get_status", "mcp__starsystem__complete_mission",
                                    "mcp__starsystem__mission_redo",
                                    "mcp__starsystem__go_home",
                                    "mcp__starlog__orient",
                                    "mcp__starship__get_course_state",
                                    "skill", "mcp__sancrev_treeshell__run_conversation_shell",
                                    "read", "glob", "grep",
                                    "task",
                                    "taskcreate", "taskupdate", "tasklist", "taskget"}:
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

            project_path = projects[0] if projects else state.get('project_path', 'unknown')
            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🚀 STARPORT]: Course plotted — configure your mission before proceeding.

{projects_msg}

🔮 CRYSTAL BALL: Scry Crystal Ball to predict which mission/flight to take based on current context.
   Use: execute_action.exec {{"server_name": "crystal-ball", "action_name": "scry", "body_schema": {{}}}}

STARPORT OPTIONS:
1. Browse flights:
   execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project_path}"}}}}

2. Create a mission type:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_create", "body_schema": {{"name": "<name>", "description": "<desc>"}}}}

3. Select existing mission:
   execute_action.exec {{"server_name": "starsystem", "action_name": "mission_select_menu", "body_schema": {{}}}}

4. Start a one-off flight (auto base mission):
   execute_action.exec {{"server_name": "starship", "action_name": "launch_routine", "body_schema": {{}}}}

5. Return home:
   execute_action.exec {{"server_name": "starsystem", "action_name": "go_home", "body_schema": {{}}}}"""
            }

    # Check if flight selected (waypoint.start called)
    if not state.get("flight_selected", False):
        # STARPORT: If no mission, DON'T auto-bounce HOME.
        # Stay in STARPORT — let agent call fly() to browse flights.
        # A plotted course without a mission is still valid (colonization, exploration).
        # Only bounce HOME if course was explicitly ended via landing_routine.

        # Always allow fly() to browse available flights
        if tool_name == "mcp__starship__fly":
            return {"allowed": True}

        # Can call waypoint.start to begin journey (with GIINT planning gate)
        if tool_name == "mcp__waypoint__start_waypoint_journey":
            starlog_path = arguments.get("starlog_path", "")
            requested_config = arguments.get("config_path", "")
            gate_result = _check_giint_planning_gate(starlog_path, requested_config, state)
            if not gate_result.get("allowed", True):
                return gate_result
            # Return gate result (may contain tool_input modification and message)
            return gate_result

        # Always allow toggle_omnisanc (escape hatch, case-insensitive for treeshell unwrap)
        if tool_name.lower() == "mcp__starsystem__toggle_omnisanc":
            return {"allowed": True}

        # Allow mission management and Canopy completion in this state
        if tool_name.lower() in {"mcp__starsystem__complete_mission", "mcp__starsystem__mission_get_status", "mcp__starsystem__mission_list", "mcp__starsystem__mission_request_extraction", "mcp__starsystem__mission_redo", "mcp__seed__home", "mcp__canopy__mark_complete", "mcp__canopy__update_item_status"}:
            return {"allowed": True}

        # go_home ONLY allowed when no active mission (must extract/abandon mission first)
        if tool_name.lower() == "mcp__starsystem__go_home":
            if state.get("mission_active"):
                mission_id = state.get("mission_id", "unknown")
                return {
                    "allowed": False,
                    "error_message": f"""🛑 🚫 🏰🌐
[🏠 HOME BLOCKED]: Cannot go_home while mission '{mission_id}' is active.

You must first extract the mission:
execute_action.exec {{"server_name": "starsystem", "action_name": "mission_request_extraction", "body_schema": {{"mission_id": "{mission_id}"}}}}

Then you can go home:
execute_action.exec {{"server_name": "starsystem", "action_name": "go_home", "body_schema": {{}}}}"""
                }
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
            project_path = projects[0] if projects else state.get('project_path', 'unknown')

            return {
                "allowed": False,
                "error_message": f"""🏰🌐
[🗺️ STARPORT]: JOURNEY MODE - STARPORT Phase

Course Details:
{projects_msg}
Description: {description}

Current Phase: STARPORT - Selecting flight configuration

Available tools (use these EXACT treeshell commands):
1. execute_action.exec {{"server_name": "starship", "action_name": "fly", "body_schema": {{"path": "{project_path}"}}}}
   Browse/explore flight configurations (can call multiple times)
2. execute_action.exec {{"server_name": "starsystem", "action_name": "mission_get_status", "body_schema": {{"mission_id": "<mission_id>"}}}}
   View mission details
3. execute_action.exec {{"server_name": "starsystem", "action_name": "mission_list", "body_schema": {{}}}}
   List all missions
4. execute_action.exec {{"server_name": "starship", "action_name": "get_course_state", "body_schema": {{}}}}
   See full course state

Next step: Choose a flight config, then start your waypoint journey:
execute_action.exec {{"server_name": "waypoint", "action_name": "start_waypoint_journey", "body_schema": {{"config_path": "<name_or_path>", "starlog_path": "{project_path}"}}}}"""
            }

    # Waypoint step enforcement (after flight selected)
    # Read actual waypoint state from Waypoint's JSON tracking
    waypoint_state = _get_waypoint_state(state.get("projects", []))
    if not waypoint_state:
        waypoint_step = 0
    else:
        waypoint_step = waypoint_state.get("completed_count", 0)

    # FLIGHT STABILIZER: Detect waypoint journey END and force session closure
    # Toggle: /tmp/flight_stabilizer_disabled.txt disables this block (used by self_compact/self_restart)
    # CONNECTS_TO: /tmp/flight_stabilizer_disabled.txt (read) — also accessed by self_compact, self_restart
    flight_stabilizer_disabled = os.path.exists("/tmp/flight_stabilizer_disabled.txt")
    waypoint_status = waypoint_state.get("status", "") if waypoint_state else ""
    if waypoint_status == "END" and state.get("session_active", False) and not flight_stabilizer_disabled:
        # Flight completed all waypoints but session still active = ghost session
        # Force agent to call end_starlog to trigger LANDING transition
        if tool_name == "mcp__starlog__end_starlog":
            return {"allowed": True}
        elif tool_name == "mcp__waypoint__navigate_to_next_waypoint":
            return {"allowed": True}
        elif tool_name == "mcp__waypoint__get_waypoint_progress":
            return {"allowed": True}
        else:
            _proj = state.get('projects', [''])[0] if state.get('projects') else ''
            return {
                "allowed": False,
                "error_message": f"""🛑 Waypoint journey COMPLETE (status=END). Session must close.
Run end_starlog to trigger LANDING phase:
  execute_action.exec {{"server_name": "starlog", "action_name": "end_starlog", "body_schema": {{"end_content": "<summary of what you accomplished>", "path": "{_proj}"}}}}"""
            }

    if waypoint_step > 0 and waypoint_step < 4:
        # Step 1: We've been served check.md, must call check() or navigate()
        if waypoint_step == 1:
            if tool_name == "mcp__starlog__check":
                return {"allowed": True}
            elif tool_name == "mcp__waypoint__navigate_to_next_waypoint":
                # Allow navigate between steps
                return {"allowed": True}
            else:
                _proj = state.get('projects', [''])[0] if state.get('projects') else ''
                return {
                    "allowed": False,
                    "error_message": f"""🛑 You tried '{tool_name}'. Not allowed at waypoint step 1.
Allowed: check, navigate_to_next_waypoint
EXPECTED — run check first:
  execute_action.exec {{"server_name": "starlog", "action_name": "check", "body_schema": {{"path": "{_proj}"}}}}
THEN advance waypoint:
  execute_action.exec {{"server_name": "waypoint", "action_name": "navigate_to_next_waypoint", "body_schema": {{"starlog_path": "{_proj}"}}}}"""
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
                _proj = state.get('projects', [''])[0] if state.get('projects') else ''
                return {
                    "allowed": False,
                    "error_message": f"""🛑 You tried '{tool_name}'. Not allowed at waypoint step 2.
Allowed: orient, init_project, navigate_to_next_waypoint
EXPECTED — run orient first:
  execute_action.exec {{"server_name": "starlog", "action_name": "orient", "body_schema": {{"path": "{_proj}"}}}}
OR if new project, init it:
  execute_action.exec {{"server_name": "starlog", "action_name": "init_project", "body_schema": {{"path": "{_proj}", "name": "<project name>", "description": "<what this project is>"}}}}
THEN advance waypoint:
  execute_action.exec {{"server_name": "waypoint", "action_name": "navigate_to_next_waypoint", "body_schema": {{"starlog_path": "{_proj}"}}}}"""
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
                _proj = state.get('projects', [''])[0] if state.get('projects') else ''
                return {
                    "allowed": False,
                    "error_message": f"""🛑 You tried '{tool_name}'. Not allowed at waypoint step 3.
Allowed: start_starlog, navigate_to_next_waypoint
EXPECTED — start a starlog session first:
  execute_action.exec {{"server_name": "starlog", "action_name": "start_starlog", "body_schema": {{"session_title": "<descriptive session title>", "start_content": "<what you are about to work on>", "session_goals": "<list of session goals>", "path": "{_proj}"}}}}
THEN advance waypoint:
  execute_action.exec {{"server_name": "waypoint", "action_name": "navigate_to_next_waypoint", "body_schema": {{"starlog_path": "{_proj}"}}}}"""
                }

    # GATE: end_starlog BLOCKED unless waypoint journey is at END
    # Agent must navigate through all waypoint steps before ending session.
    # The flight stabilizer (above) detects END and forces end_starlog. That's the ONLY path.
    if tool_name == "mcp__starlog__end_starlog" and waypoint_state and waypoint_status != "END":
        _proj = state.get('projects', [''])[0] if state.get('projects') else ''
        return {
            "allowed": False,
            "error_message": f"""🛑 You tried end_starlog but the waypoint journey is still active (step {waypoint_step}).
You must navigate through all remaining waypoint steps first.
Run this to advance:
  execute_action.exec {{"server_name": "waypoint", "action_name": "navigate_to_next_waypoint", "body_schema": {{"starlog_path": "{_proj}"}}}}
Complete your flight before ending the session."""
        }

    # Step 4+ (work loop) — all tools EXCEPT end_starlog (gated by waypoint completion)
    if tool_name == "mcp__starlog__end_starlog":
        wp_status = waypoint_state.get("status", "") if waypoint_state else ""
        if wp_status != "END":
            _proj = state.get('projects', [''])[0] if state.get('projects') else ''
            return {
                "allowed": False,
                "error_message": f"""🛑 Cannot end session — flight is not complete (waypoint status: {wp_status or 'unknown'}).
Navigate through remaining waypoint steps first:
  execute_action.exec {{"server_name": "waypoint", "action_name": "navigate_to_next_waypoint", "body_schema": {{"starlog_path": "{_proj}"}}}}
The flight's last step will prompt you to end the session."""
            }
    return {"allowed": True}

def read_omnisanc_mode() -> str:
    """Read OMNISANC mode from control file.

    Single switch: /tmp/heaven_data/omnisanc_core/.omnisanc_disabled
    - File exists → "freestyle": No SM enforcement, but Flight Predictor capture runs
    - File absent → "enforced": Full SM enforcement + capture

    Toggled by: /home/GOD/bin/omnisanc

    Returns: "enforced" or "freestyle"
    """
    # CONNECTS_TO: /tmp/heaven_data/omnisanc_core/.omnisanc_disabled (read) — toggled by /home/GOD/bin/omnisanc, starsystem toggle_omnisanc
    disabled_file = Path("/tmp/heaven_data/omnisanc_core/.omnisanc_disabled")
    if disabled_file.exists():
        return "freestyle"
    return "enforced"


def on_tool_use(tool_name: str, arguments: dict) -> dict:
    """
    OMNISANC Core hook - enforces Home/Journey workflow

    Returns:
        dict with 'allowed' boolean and optional 'error_message'
    """
    try:
        # THREE-MODE SYSTEM: enforced, freestyle, disabled
        mode = read_omnisanc_mode()

        # PBML RATCHET PreToolUse GATE: Runs in ALL modes including disabled
        # The ratchet is forward-only lane validation — always enforced even in freestyle
        if tool_name == "TaskUpdate" and arguments.get("status") == "completed":
            TREEKANBAN_RATCHET = {
                "backlog": ["plan", "blocked"],
                "plan": ["blocked", "build"],
                "blocked": ["backlog", "plan", "archive"],
                "build": ["measure", "blocked"],
                "measure": ["learn", "blocked"],
                "learn": ["archive", "blocked"],
                "archive": [],
            }
            TREEKANBAN_DONE_STATUS = "archive"
            try:
                from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient
                giint_env = get_strata_mcp_env("giint-llm-intelligence")
                board_name = giint_env.get("GIINT_TREEKANBAN_BOARD")
                if board_name:
                    client = HeavenBMLSQLiteClient()
                    task_id = arguments.get("taskId", "")
                    task_data = resolve_claude_task(task_id) if task_id else {}
                    subject = task_data.get("subject", arguments.get("subject", ""))
                    if not subject:
                        logger.warning(f"[PBML Ratchet] Could not resolve subject for taskId={task_id}")
                    all_cards = client.get_all_cards(board_name)
                    for card in all_cards:
                        card_tags_str = card.get("tags", "[]")
                        card_tags = json.loads(card_tags_str) if isinstance(card_tags_str, str) else card_tags_str
                        if "claude-task" in card_tags and card.get("title") == subject:
                            current_lane = card.get("lane") or card.get("status", "backlog")
                            valid_next = TREEKANBAN_RATCHET.get(current_lane, [])
                            if TREEKANBAN_DONE_STATUS not in valid_next:
                                return {
                                    "allowed": False,
                                    "error_message": f"[PBML Ratchet] Cannot archive '{subject}' from '{current_lane}'. Valid next: {valid_next}. Move card through the ratchet first."
                                }
                            break
            except Exception as e:
                logger.warning(f"[PBML Ratchet PreToolUse] Check failed (allowing through): {e}")

        if mode == "disabled":
            # Total escape hatch - skip OMNISANC enforcement (ratchet already ran above)
            return {"allowed": True}

        if mode == "freestyle":
            # Skip enforcement but Flight Predictor capture runs in PostToolUse
            logger.debug(f"[FREESTYLE] Allowing {tool_name} without enforcement")
            return {"allowed": True}

        # UNWRAP STRATA/GNOSYS-KIT CALLS: Get the actual tool being called
        # This handles mcp__strata__execute_action and mcp__gnosys_kit__run_conversation_shell
        from strata_unwrap import get_actual_tool_name, get_actual_tool_input
        request_data = {"tool_name": tool_name, "tool_input": arguments}
        actual_tool_name = get_actual_tool_name(request_data)
        actual_arguments = get_actual_tool_input(request_data)

        # Use unwrapped names for all subsequent checks
        tool_name = actual_tool_name
        arguments = actual_arguments

        # REMOVED: GNOSYS get_next_task flip — no longer needed.
        # Conductor's /self/inject message tells GNOSYS to call tk_next_task with from_conductor=false.
        # GNOSYS never calls get_next_task on its own — only when conductor dispatches.

        # GNOSYS_KIT / STRATA META-TOOLS WHITELIST: Always allow discovery/docs tools
        # These are read-only tools for exploring what's available
        # Supports both old (mcp__strata__) and new (mcp__gnosys_kit__) prefixes
        meta_tool_suffixes = [
            "discover_server_actions",
            "get_action_details",
            "search_documentation",
            "handle_auth_failure",
            "manage_servers",
            "execute_action",
            "search_mcp_catalog",
        ]
        for prefix in ["mcp__strata__", "mcp__gnosys_kit__", "mcp__sancrev_treeshell__"]:
            if any(tool_name == f"{prefix}{suffix}" for suffix in meta_tool_suffixes):
                return {"allowed": True, "reason": "gnosys_kit_meta_tool_whitelisted"}

        # TREESHELL WHITELIST: Always allow treeshell meta operations
        # execute_action calls get unwrapped above and validated as the actual tool
        # Other commands (nav, manage_servers, etc) stay as run_conversation_shell and are always allowed
        treeshell_tools = [
            "mcp__gnosys_kit__run_conversation_shell",
            "mcp__skill_manager_treeshell__run_conversation_shell",
            "mcp__sancrev_treeshell__run_conversation_shell",
        ]
        if tool_name in treeshell_tools:
            return {"allowed": True, "reason": "treeshell_whitelisted"}

        # OMNISANC TOGGLE WHITELIST: Always allow toggling OMNISANC on/off
        # This ensures users can always disable OMNISANC if needed (case-insensitive for treeshell unwrap)
        if tool_name.lower() == "mcp__starsystem__toggle_omnisanc":
            return {"allowed": True, "reason": "omnisanc_toggle_whitelisted"}

        # SELF-MANAGEMENT WHITELIST: self_compact/self_restart must work in ALL states
        # These are critical escape hatches that must never be blocked
        if tool_name.lower() == "mcp__self-claude__self_claude":
            return {"allowed": True, "reason": "self_claude_globally_whitelisted"}
        if tool_name == "Bash":
            cmd = (arguments or {}).get("command", "").strip()
            if cmd.startswith("self_compact") or cmd.startswith("self_restart"):
                return {"allowed": True, "reason": "self_management_globally_whitelisted"}

        state = get_course_state()

        # GIINT PLANNING GATE: Auto-redirect to planning flight if no ready tasks
        # This runs AFTER strata_unwrap so tool_name is the actual waypoint call
        # DEBUG: Log every tool that reaches this point
        with open('/tmp/omnisanc_gate_debug.log', 'a') as f:
            f.write(f"GATE CHECK: tool={tool_name}, args={arguments}\n")
        if tool_name == "mcp__waypoint__start_waypoint_journey":
            starlog_path = arguments.get("starlog_path", "")
            requested_config = arguments.get("config_path", "")
            with open('/tmp/omnisanc_gate_debug.log', 'a') as f:
                f.write(f"GATE TRIGGERED: starlog={starlog_path}, config={requested_config}\n")
            gate_result = _check_giint_planning_gate(starlog_path, requested_config, state)
            with open('/tmp/omnisanc_gate_debug.log', 'a') as f:
                f.write(f"GATE RESULT: {gate_result}\n")
            # If gate blocks, return immediately with instructions
            if not gate_result.get("allowed", True):
                logger.info(f"[GIINT Planning Gate] Blocked — instructing agent to use planning flight")
                return gate_result

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

        # SESSION END SHIELD: DISABLED — was causing stale mission deadlock across compaction
        # Shield counter permanently 0 so it never blocks. See Bug_Omnisanc_Session_Shield_Removed_Mar01
        pass

        # JIT GIINT PROJECT CONSTRUCTION: Before giint.respond(), auto-create project hierarchy
        if tool_name == "mcp__giint-llm-intelligence__core__respond" and GIINT_AVAILABLE:
            try:
                # resolve project_path → project_id for JIT hierarchy construction
                _project_path = arguments.get("project_path")
                project_id = None
                if _project_path:
                    try:
                        from llm_intelligence.projects import get_project_by_dir
                        _lookup = get_project_by_dir(_project_path)
                        project_id = _lookup.get("project_id")
                    except Exception as e:
                        logger.debug(f"JIT: Could not resolve project_path to project_id: {e}")
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

        # TASK CONTEXT VALIDATION: Enforce metadata on task creation and completion
        # TaskCreate requires context_deps (what files to read)
        if tool_name == "TaskCreate":
            metadata = arguments.get("metadata", {}) or {}
            if "context_deps" not in metadata:
                return {
                    "allowed": False,
                    "error_message": """🏰🌐
[📋 TASK]: CONTEXT REQUIRED: Cannot create task without context_deps.

When creating a task, you MUST specify what files you need to read:

TaskCreate(
    subject="...",
    description="...",
    metadata={
        "context_deps": ["files you need to read to understand/do this task"]
    }
)

This enables upfront context planning for GIINT."""
                }

        # When completing a task, agent MUST provide full context metadata for GIINT
        if tool_name == "TaskUpdate":
            status = arguments.get("status", "")
            if status == "completed":
                metadata = arguments.get("metadata", {}) or {}
                required_fields = ["files_touched", "context_deps", "key_insight"]
                missing_fields = [f for f in required_fields if f not in metadata]

                if missing_fields:
                    return {
                        "allowed": False,
                        "error_message": f"""🏰🌐
[📋 TASK]: CONTEXT REQUIRED: Cannot complete task without context metadata.

Missing fields: {', '.join(missing_fields)}

When completing a task, you MUST include metadata:

TaskUpdate(
    taskId="...",
    status="completed",
    metadata={{
        "files_touched": ["list of files you modified"],
        "context_deps": ["files you read to understand the task"],
        "key_insight": "what pattern or insight you discovered"
    }}
)

This enables the GIINT contextualization protocol."""
                    }

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
            result = validate_journey_mode(tool_name, state, arguments)

            # Track when waypoint journey starts (unlocks Journey mode)
            if tool_name == "mcp__waypoint__start_waypoint_journey" and result.get("allowed", False):
                state["flight_selected"] = True
                # Mission-driven starts bypass fly() — set fly_called too
                if state.get("mission_active"):
                    state["fly_called"] = True
                if not state.get("jit_starlog_initialized", False):
                    state["waypoint_step"] = 1  # Initialize waypoint sequence (only if not JIT)
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
            # Check for actual success in tool response (not "allowed" which is a PreToolUse concept)
            if tool_name == "mcp__starship__landing_routine":
                tool_ok = _check_tool_success(result)
                if tool_ok and state.get("needs_review", False):
                    state["landing_routine_called"] = True
                    save_course_state(state)
                elif not tool_ok:
                    logger.warning(f"[LANDING] landing_routine did NOT succeed — step 1 not advanced")

            if tool_name == "mcp__starship__session_review":
                tool_ok = _check_tool_success(result)
                if tool_ok and state.get("needs_review", False):
                    state["session_review_called"] = True
                    save_course_state(state)
                elif not tool_ok:
                    logger.warning(f"[LANDING] session_review did NOT succeed — step 2 not advanced")

            # NOTE: giint.respond LANDING advancement is in on_tool_result() (PostToolUse)
            # where the actual tool output is available, not here in on_tool_use (PreToolUse)

            # NOTE: end_starlog state mutation moved to on_tool_result (PostToolUse)
            # so LANDING only enters AFTER end_starlog actually succeeds.
            # Previously was here in PreToolUse, which caused LANDING entry even when
            # WARPCORE blocked end_starlog execution.

            # Track when plot_course is allowed (PreToolUse)
            # Actual state update happens in PostToolUse after success

            # Track when mission starts
            if tool_name.lower() == "mcp__starsystem__mission_start" and result.get("allowed", False):
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

            # Handle waypoint abort — ALWAYS allowed, even with active session (#162)
            # Abort is the escape hatch. It cleans up everything.
            if tool_name == "mcp__waypoint__abort_waypoint_journey":
                if result.get("allowed", False):
                    # Clean up session + waypoint state
                    if state.get("session_active", False):
                        state["session_active"] = False
                        state["needs_review"] = False  # Skip LANDING on abort
                    state["flight_selected"] = False
                    state["waypoint_step"] = 0
                    _cleanup_waypoint_state(state.get("projects", []))
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

def _check_tool_success(result) -> bool:
    """Check if a tool result indicates success.

    Handles multiple result formats: dict, string, list of content blocks.
    Returns True only when there's positive evidence of success.
    """
    try:
        if isinstance(result, dict):
            # Direct MCP response: {"success": true, ...}
            if "success" in result:
                return bool(result["success"])
            # Error response: {"error": "..."}
            if "error" in result:
                return False
            # No success/error key — assume success if no error indicators
            return True
        elif isinstance(result, str):
            lower = result.lower()
            if '"error"' in lower or "error:" in lower or "traceback" in lower:
                return False
            if '"success": true' in lower or '"success":true' in lower:
                return True
            # String with no error indicators — assume success
            return "error" not in lower
        elif isinstance(result, list):
            # List of content blocks — convert to string and check
            result_str = str(result).lower()
            if "error" in result_str or "traceback" in result_str:
                return False
            return True
        else:
            return False
    except Exception:
        return False


def _is_treeshell_failure(result: any, raw_tool_name: str) -> bool:
    """Check if a treeshell-wrapped call's result indicates the inner operation failed.

    Treeshell calls always "succeed" from Claude Code's perspective (the MCP returned
    a response), but the inner operation may have failed. This checks the result
    content for error indicators.

    Args:
        result: The tool response content
        raw_tool_name: The ORIGINAL tool name before strata unwrap
    """
    from strata_unwrap import TREESHELL_TOOLS
    if raw_tool_name not in TREESHELL_TOOLS:
        return False

    result_str = str(result).lower() if result else ""
    if not result_str:
        return False

    error_indicators = [
        "error:",
        '"error"',          # JSON error key: {"error": "..."}
        "not connected",
        "not configured",
        "failed to",
        "traceback (most recent",
        "exception:",
        "server disconnected",
        "connection refused",
        "validation failed",
    ]
    return any(indicator in result_str for indicator in error_indicators)


def on_tool_result(tool_name: str, arguments: dict, result: any, raw_tool_name: str = "") -> dict:
    """
    OMNISANC PostToolUseHook - fires after tool completes

    Handles:
    - Session score computation after end_starlog
    - Mission score computation after request_extraction

    Returns:
        dict with any post-processing results
    """
    try:
        # UNIVERSAL TREESHELL FAILURE GUARD
        # If the call was treeshell-wrapped and the inner operation failed,
        # skip ALL state mutations. The outer treeshell call "succeeded" but
        # the inner MCP operation did not.
        if _is_treeshell_failure(result, raw_tool_name):
            logger.warning(f"[TREESHELL FAILURE] Inner operation failed for {tool_name}, skipping state mutations. Result: {str(result)[:200]}")
            return {"success": False, "reason": "treeshell_inner_failure"}

        # === SEMANTIC ADDRESS RESOLUTION ===
        # When treeshell calls go through navigation-then-exec, strata unwrap
        # can't identify the tool (bare "exec {args}"). But treeshell responses
        # ALWAYS contain "Semantic address: `x.y.z`". Parse it and resolve.
        _TREESHELL_TOOLS = {
            'mcp__sancrev_treeshell__run_conversation_shell',
            'mcp__gnosys_kit__run_conversation_shell',
            'mcp__skill_manager_treeshell__run_conversation_shell',
        }
        _SEMANTIC_LEAF_TO_TOOL = {
            "tk_add_deliverable": "mcp__giint-llm-intelligence__planning__add_deliverable_to_component",
            "tk_add_task": "mcp__giint-llm-intelligence__planning__add_task_to_deliverable",
            "tk_update_task": "mcp__giint-llm-intelligence__planning__update_task_status",
        }
        if tool_name in _TREESHELL_TOOLS or raw_tool_name in _TREESHELL_TOOLS:
            _response_text = ""
            if isinstance(result, str):
                _response_text = result
            elif isinstance(result, list):
                for _item in result:
                    if isinstance(_item, dict):
                        _response_text += _item.get("text", "")
            elif isinstance(result, dict):
                _response_text = result.get("text", str(result))

            _sa_marker = 'Semantic address: `'
            _sa_start = _response_text.find(_sa_marker)
            if _sa_start != -1:
                _sa_start += len(_sa_marker)
                _sa_end = _response_text.find('`', _sa_start)
                if _sa_end != -1:
                    _semantic_address = _response_text[_sa_start:_sa_end]
                    _leaf = _semantic_address.rsplit('.', 1)[-1]
                    _resolved = _SEMANTIC_LEAF_TO_TOOL.get(_leaf)
                    if _resolved:
                        tool_name = _resolved
                        _cmd = arguments.get("command", "")
                        _exec_idx = _cmd.find("exec ")
                        if _exec_idx != -1:
                            try:
                                arguments = json.loads(_cmd[_exec_idx + 5:])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    logger.info(f"[SEMANTIC ADDR] addr={_semantic_address} leaf={_leaf} resolved={_resolved or 'none'} tool_name={tool_name}")
        # === END SEMANTIC ADDRESS RESOLUTION ===

        # Zone transition narration (injected as context via router stdout)
        narration = None

        # === end_starlog: Session end + LANDING entry (PostToolUse only) ===
        # MUST be in PostToolUse so LANDING only enters AFTER end_starlog actually succeeds.
        if tool_name == "mcp__starlog__end_starlog" and _check_tool_success(result):
            state = get_course_state()
            was_base_mission = is_base_mission(state)

            state["session_active"] = False
            state["waypoint_step"] = 0
            state["flight_selected"] = False
            state["fly_called"] = False
            state["jit_starlog_initialized"] = False
            state["session_end_shield_count"] = 1
            state["session_shielded"] = True

            if was_base_mission:
                state["course_plotted"] = False
                state["mission_active"] = False
                state["mission_id"] = None
                state["needs_review"] = False
                state["landing_routine_called"] = False
                state["session_review_called"] = False
                state["giint_respond_called"] = False
                save_course_state(state)
                narration = "✅ Session complete. You're back HOME."
            else:
                state["needs_review"] = True
                state["landing_routine_called"] = False
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
                                loaded_mission.session_sequence[current_step].status = "completed"
                                loaded_mission.session_sequence[current_step].completed_at = datetime.now().isoformat()
                                loaded_mission.current_step += 1
                                loaded_mission.metrics.sessions_completed += 1
                                mission.save_mission(loaded_mission)
                                logger.info(f"Marked mission session {current_step} as completed, advanced to step {loaded_mission.current_step}")
                    except Exception as e:
                        logger.error(f"Failed to update mission session status: {e}")

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

            # Store description — never overwrite with None
            desc = arguments.get("description")
            if desc:
                state["description"] = desc

            # Store STARPORT fields (Phase 1)
            state["domain"] = arguments.get("domain") or "HOME"
            state["subdomain"] = arguments.get("subdomain")
            state["process"] = arguments.get("process")

            # Generate qa_id for base mission (plot_course creates base mission with mission_id)
            # SELF-CONTAINED: Try result first (base mission ID), then state fallback
            mission_id = state.get("mission_id")
            if not mission_id:
                # Extract from plot_course result (base mission auto-created by STARSYSTEM MCP)
                try:
                    result_str = str(result) if result else ""
                    if "mission_id" in result_str:
                        import re
                        match = re.search(r'"mission_id":\s*"([^"]+)"', result_str)
                        if match:
                            mission_id = match.group(1)
                            state["mission_id"] = mission_id
                            state["mission_active"] = True
                            logger.info(f"PostToolUse: Extracted mission_id from plot_course result: {mission_id}")
                except Exception as e:
                    logger.error(f"PostToolUse: Failed to extract mission_id from result: {e}")
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

                        # Atomic STARSYSTEM init: also init starlog alongside GIINT
                        if STARLOG_AVAILABLE:
                            try:
                                sl = Starlog()
                                sl.init_project(
                                    path=project_dir,
                                    name=mission_id,
                                    description=f"Auto-initialized by mission {mission_id}"
                                )
                                state["jit_starlog_initialized"] = True
                                state["waypoint_step"] = 3  # Skip steps 1-2 in enforcement
                                logger.info(f"JIT starlog init for base mission: {mission_id} at {project_dir}")
                            except Exception as e:
                                logger.error(f"JIT starlog init failed for base mission: {e}", exc_info=True)

                    except Exception as e:
                        logger.error(f"Failed to create GIINT project for base mission: {e}", exc_info=True)

            save_course_state(state)
            logger.info(f"Course state updated: {project_paths} [domain={state['domain']}, subdomain={state['subdomain']}, process={state['process']}]")
            narration = _screen_starport(state)

        # Narrate PLANETSIDE transition after start_starlog
        if tool_name == "mcp__starlog__start_starlog":
            narration = _screen_journey(get_course_state())

        # Generate qa_id after mission_start succeeds
        # SELF-CONTAINED: Extract mission_id from arguments, not course state.
        # PreToolUse state-setting is bypassed when called through treeshell whitelist.
        if tool_name.lower() == "mcp__starsystem__mission_start":
            state = get_course_state()
            # Get mission_id from arguments first (treeshell-safe), fallback to state
            mission_id = arguments.get("mission_id") or state.get("mission_id")
            if mission_id:
                # ALWAYS update mission state — overwrites base_mission if one was auto-created
                old_mission = state.get("mission_id")
                if old_mission and old_mission != mission_id:
                    logger.info(f"PostToolUse: Replacing mission {old_mission} with {mission_id}")
                state["mission_active"] = True
                state["mission_id"] = mission_id
                state["mission_step"] = 0
                state["course_plotted"] = True
                # Load projects from mission file
                mission_file = f"/tmp/heaven_data/missions/{mission_id}.json"
                try:
                    with open(mission_file, 'r') as f:
                        mission_data = json.load(f)
                        projects = list(set(
                            session["project_path"]
                            for session in mission_data["session_sequence"]
                        ))
                        state["projects"] = projects
                except Exception as e:
                    logger.error(f"PostToolUse: Failed to load mission projects: {e}")
                    state["projects"] = []
                logger.info(f"PostToolUse: Mission state set for {mission_id}")

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

                        # Atomic STARSYSTEM init: also init starlog alongside GIINT
                        if STARLOG_AVAILABLE:
                            try:
                                sl = Starlog()
                                sl.init_project(
                                    path=project_dir,
                                    name=mission_id,
                                    description=f"Auto-initialized by mission {mission_id}"
                                )
                                state["jit_starlog_initialized"] = True
                                state["waypoint_step"] = 3  # Skip steps 1-2 in enforcement
                                save_course_state(state)
                                logger.info(f"JIT starlog init for formal mission: {mission_id} at {project_dir}")
                            except Exception as e:
                                logger.error(f"JIT starlog init failed for formal mission: {e}", exc_info=True)

                    except Exception as e:
                        logger.error(f"Failed to create GIINT project for formal mission: {e}", exc_info=True)

        # Clear mission state after extraction succeeds
        if tool_name.lower() == "mcp__starsystem__mission_request_extraction":
            state = get_course_state()

            # Pause mission - return to HOME but keep mission_id (top of queue)
            state["mission_active"] = False
            # Keep mission_id - mission paused, can resume or end by plotting new course
            state["mission_step"] = 0
            state["course_plotted"] = False
            state["flight_selected"] = False
            state["fly_called"] = False
            state["waypoint_step"] = 0
            state["jit_starlog_initialized"] = False  # Clear JIT flag
            _cleanup_waypoint_state(state.get("projects", []))

            save_course_state(state)
            logger.info("Mission extraction completed - state cleared to HOME")
            narration = _screen_home(state)

        # LANDING Step 3: Advance state after giint.respond succeeds
        if tool_name == "mcp__giint-llm-intelligence__core__respond":
            state = get_course_state()
            if state.get("needs_review", False) and state.get("session_review_called", False):
                # Parse result - can be list (treeshell content blocks), dict, or string
                giint_succeeded = False
                try:
                    result_str = str(result).lower() if result else ""
                    if isinstance(result, dict):
                        if "allowed" in result and "success" not in result:
                            logger.warning(f"[LANDING] giint result is CAVE metadata: {str(result)[:200]}")
                        else:
                            giint_succeeded = bool(result.get("success", False))
                    elif isinstance(result, list):
                        # Treeshell content blocks - check text content for success
                        for block in result:
                            if isinstance(block, dict):
                                text = block.get("text", "")
                                if '"success":true' in text.replace(" ", "") or '"success": true' in text:
                                    giint_succeeded = True
                                    break
                    elif '"success"' in result_str:
                        giint_succeeded = '"success": true' in result_str or '"success":true' in result_str
                    elif result and "error" not in result_str and "traceback" not in result_str:
                        giint_succeeded = True
                except Exception:
                    giint_succeeded = False

                if giint_succeeded:
                    state["giint_respond_called"] = True
                    state["needs_review"] = False
                    state["landing_routine_called"] = False
                    state["session_review_called"] = False
                    state["giint_respond_called"] = False
                    save_course_state(state)
                    logger.info("[LANDING] giint.respond succeeded — LANDING complete")

                    # Use shared screen helpers for post-LANDING narration
                    if state.get("mission_id"):
                        narration = _screen_starport(state)
                    else:
                        narration = _screen_home(state)
                else:
                    logger.warning(f"[LANDING] giint.respond did NOT succeed. Result type: {type(result).__name__}, preview: {str(result)[:200]}")

        # Return to STARPORT after mission completion (course stays plotted)
        if tool_name.lower() == "mcp__starsystem__complete_mission":
            state = get_course_state()

            # Mission complete - return to STARPORT, keep course plotted
            state["mission_active"] = False
            state["mission_id"] = None
            state["mission_step"] = 0
            state["flight_selected"] = False
            state["fly_called"] = False
            state["waypoint_step"] = 0
            state["jit_starlog_initialized"] = False  # Clear JIT flag
            _cleanup_waypoint_state(state.get("projects", []))

            save_course_state(state)
            logger.info("Mission completed - returned to STARPORT (course still plotted)")
            narration = _screen_starport(state)

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

        # Re-activate course state after mission_redo (same as mission_start)
        if tool_name.lower() == "mcp__starsystem__mission_redo":
            state = get_course_state()
            mission_id = arguments.get("mission_id") or state.get("mission_id")
            if mission_id:
                state["mission_active"] = True
                state["mission_id"] = mission_id
                state["mission_step"] = 0
                state["course_plotted"] = True
                state["flight_selected"] = False
                state["fly_called"] = False
                state["waypoint_step"] = 0
                state["needs_review"] = False
                state["landing_routine_called"] = False
                state["session_review_called"] = False
                state["giint_respond_called"] = False
                # Load projects from mission file
                mission_file = f"/tmp/heaven_data/missions/{mission_id}.json"
                try:
                    with open(mission_file, 'r') as f:
                        mission_data = json.load(f)
                        projects = list(set(
                            session["project_path"]
                            for session in mission_data["session_sequence"]
                        ))
                        state["projects"] = projects
                except Exception as e:
                    logger.error(f"PostToolUse: Failed to load mission projects for redo: {e}")
                qa_id = f"{mission_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                state["qa_id"] = qa_id
                save_course_state(state)
                logger.info(f"Mission redo - course state re-activated for {mission_id}")
                narration = _screen_starport(state)

        # Return to HOME after go_home (clears course)
        if tool_name.lower() == "mcp__starsystem__go_home":
            state = get_course_state()
            _cleanup_waypoint_state(state.get("projects", []))
            state["course_plotted"] = False
            state["mission_active"] = False
            state["mission_id"] = None
            state["mission_step"] = 0
            state["flight_selected"] = False
            state["fly_called"] = False
            state["waypoint_step"] = 0
            state["jit_starlog_initialized"] = False
            state["projects"] = []
            save_course_state(state)
            logger.info("go_home - returned to HOME, course cleared")
            narration = _screen_home(state)

        # Narrate LANDING transition after end_starlog
        if tool_name == "mcp__starlog__end_starlog":
            narration = _screen_landing(get_course_state())

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
        elif tool_name.lower() == "mcp__starsystem__mission_request_extraction" and REGISTRY_AVAILABLE:
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
                "mcp__giint-llm-intelligence__planning__update_task_status": "update_task",
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

                                elif sync_type == "update_task":
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
                                            sync_result = carton_sync.update_task_in_carton(
                                                project_id, feature_name, component_name, deliverable_name, task_id, task_data
                                            )
                                            logger.info(f"Updated GIINT task '{project_id}/{feature_name}/{component_name}/{deliverable_name}/{task_id}' in Carton")

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
                                                # Full semantic tags — starsystem + assignee required for dispatch
                                                tags = ["giint", project_id, "deliverable", deliverable_name,
                                                        f"starsystem:{project_id}", "assignee:ai-only"]

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

                                                # Description = GIINT path pointer. Real content on CartON concept.
                                                giint_path = f"GIINT: {project_id}/{feature_name}/{component_name}/{deliverable_name}"

                                                card_data = {
                                                    "board": board_name,
                                                    "title": deliverable_name,
                                                    "description": giint_path,
                                                    "status": "backlog",
                                                    "priority": next_priority,
                                                    "tags": json.dumps(tags)
                                                }

                                                card_result = client._make_request("POST", "/api/sqlite/cards", card_data)

                                                logger.info(f"Pushed GIINT deliverable '{deliverable_name}' with priority {next_priority}: {card_result}")

                                                # Check if deliverable has vendored OperadicFlows
                                                operadic_flow_ids = deliverable_data.get("operadic_flow_ids", [])
                                                if operadic_flow_ids:
                                                    logger.info(f"Deliverable has {len(operadic_flow_ids)} vendored OperadicFlows, creating pattern cards")
                                                    try:
                                                        # PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
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
                                                # Full semantic tags — assignee from task data
                                                task_assignee = task_data.get("assignee", "AI-Only").lower().replace("+", "-").replace(" ", "-")
                                                tags = ["giint", project_id, "deliverable", deliverable_name, "task", task_id,
                                                        f"starsystem:{project_id}", f"assignee:{task_assignee}"]

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

                                                    # Description = GIINT path pointer. Real content on CartON concept.
                                                    giint_path = f"GIINT: {project_id}/{feature_name}/{component_name}/{deliverable_name}/{task_id}"

                                                    card_data = {
                                                        "board": board_name,
                                                        "title": task_data.get("description", task_id),
                                                        "description": giint_path,
                                                        "status": "backlog",
                                                        "priority": task_priority,
                                                        "tags": json.dumps(tags)
                                                    }

                                                    card_result = client._make_request("POST", "/api/sqlite/cards", card_data)

                                                    logger.info(f"Pushed GIINT task '{task_id}' with priority {task_priority}: {card_result}")

                            except Exception as e:
                                logger.error(f"GIINT-TreeKanban sync failed for {project_id} (non-critical): {e}", exc_info=True)

                except Exception as e:
                    logger.error(f"GIINT-TreeKanban sync import/execution failed (non-critical): {e}", exc_info=True)

        # PBML Ratchet — valid lanes and transitions
        # backlog → plan → blocked → build → measure → learn → archive
        TREEKANBAN_LANES = ["backlog", "plan", "blocked", "build", "measure", "learn", "archive"]
        TREEKANBAN_RATCHET = {
            "backlog": ["plan", "blocked"],
            "plan": ["blocked", "build"],
            "blocked": ["backlog", "plan", "archive"],
            "build": ["measure", "blocked"],
            "measure": ["learn", "blocked"],
            "learn": ["archive", "blocked"],
            "archive": [],  # terminal — new work = new card at backlog
        }
        TREEKANBAN_DONE_STATUS = "archive"

        # Claude Code Task → CartON mirror only (Odyssey System)
        # CC tasks are agent execution scratchpad — NOT routed to GIINT/TK.
        # GIINT/TK is human planning level. Agent subtasks mirror to CartON for observability.
        # CONNECTS_TO: /tmp/heaven_data/cc_task_mirror/ (write) — TaskCreate/TaskUpdate mirror to JSON for CartON sync
        _CC_MIRROR_DIR = "/tmp/heaven_data/cc_task_mirror"

        if tool_name == "TaskCreate":
            try:
                subject = arguments.get("subject", "Untitled Task")
                description = arguments.get("description", "")
                metadata = arguments.get("metadata", {}) or {}
                concept_name = "Cc_Subtask_" + subject.replace(" ", "_").replace("-", "_")[:80]
                # Full GIINT hierarchy path — CC tasks MUST declare where they belong
                giint_project = metadata.get("giint_project")
                giint_feature = metadata.get("giint_feature")
                giint_component = metadata.get("giint_component")
                giint_deliverable = metadata.get("giint_deliverable")
                giint_path = f"{giint_project}/{giint_feature}/{giint_component}/{giint_deliverable}" if giint_project else "ORPHAN"
                os.makedirs(_CC_MIRROR_DIR, exist_ok=True)
                mirror_data = {
                    "concept_name": concept_name,
                    "description": description,
                    "is_a": "Cc_Subtask",
                    "part_of": giint_deliverable or giint_project or "Cc_Orphan_Tasks",
                    "giint_path": giint_path,
                    "giint_project": giint_project,
                    "giint_feature": giint_feature,
                    "giint_component": giint_component,
                    "giint_deliverable": giint_deliverable,
                    "status": "created",
                    "ts": datetime.now().isoformat(),
                    "context_deps": metadata.get("context_deps", [])
                }
                mirror_path = os.path.join(_CC_MIRROR_DIR, f"{concept_name}.json")
                with open(mirror_path, "w") as f:
                    json.dump(mirror_data, f, indent=2)
                logger.info(f"[TaskCreate→CartON] Mirrored '{subject}' → {giint_path}")
            except Exception as e:
                logger.error(f"[TaskCreate→CartON] Mirror failed (non-critical): {e}")

        if tool_name == "TaskUpdate":
            new_status = arguments.get("status", "")
            task_id = arguments.get("taskId", "")
            task_data = resolve_claude_task(task_id) if task_id else {}
            subject = task_data.get("subject", "")
            task_metadata = task_data.get("metadata", {}) or {}
            if subject:
                try:
                    concept_name = "Cc_Subtask_" + subject.replace(" ", "_").replace("-", "_")[:80]
                    mirror_path = os.path.join(_CC_MIRROR_DIR, f"{concept_name}.json")
                    existing = {}
                    if os.path.exists(mirror_path):
                        with open(mirror_path, "r") as f:
                            existing = json.load(f)
                    existing["status"] = new_status
                    existing["updated_at"] = datetime.now().isoformat()
                    if new_status == "completed":
                        existing["files_touched"] = task_metadata.get("files_touched", [])
                        existing["key_insight"] = task_metadata.get("key_insight", "")
                        existing["context_deps"] = task_metadata.get("context_deps", [])
                    with open(mirror_path, "w") as f:
                        json.dump(existing, f, indent=2)
                    logger.info(f"[TaskUpdate→CartON] Updated '{subject}' → {new_status}")
                except Exception as e:
                    logger.error(f"[TaskUpdate→CartON] Mirror failed (non-critical): {e}")

        # OPERA-TreeKanban sync hook - spawn OperadicFlow cards when vendored
        if tool_name == "mcp__opera__vendor_operadic_flow":
            logger.info(f"[OPERA-TreeKanban Hook] vendor_operadic_flow detected")
            try:
                from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient
                # PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
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
                                # PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
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

        # === MEMORY RECOMPILE CHAIN (Task #21) ===
        # After get_next_task_from_treekanban returns, recompile MEMORY.md
        # so agent sees expanded HC context on next turn (hot-reload).
        # GIINT's _ensure_giint_hierarchy_in_carton already:
        #   - Created full starsystem collection hierarchy (Task_Collections, Done_Signal_Collections, etc.)
        #   - Created HC in Task_Collections with full GIINT hierarchy (Project→Feature→Component→Deliverable→Task)
        #   - Set /tmp/active_hypercluster.txt
        if tool_name == "mcp__giint-llm-intelligence__get_next_task_from_treekanban":
            try:
                # Parse the tool result to get giint_metadata (same parsing as auto-vendor)
                recompile_result_data = None
                if isinstance(result, str):
                    recompile_result_data = json.loads(result)
                elif isinstance(result, list) and len(result) > 0:
                    text_content = result[0].get("text")
                    if text_content:
                        recompile_result_data = json.loads(text_content)
                else:
                    recompile_result_data = result

                # CONNECTS_TO: /tmp/active_hypercluster.txt (read) — written by GIINT _ensure_giint_hierarchy_in_carton
                active_hc_file = Path("/tmp/active_hypercluster.txt")
                if active_hc_file.exists() and recompile_result_data:
                    hc_name = active_hc_file.read_text().strip()
                    logger.info(f"[Memory Recompile] Active HC: {hc_name}")

                    # Extract task concept name from giint_metadata
                    # Result structure: {card: {giint_metadata: {task_id, project_id, ...}}}
                    card = recompile_result_data.get("card", {})
                    giint_meta = card.get("giint_metadata", {})
                    task_id = giint_meta.get("task_id") if giint_meta else None
                    task_concept = f"Giint_Task_{task_id.replace('-', '_').replace(' ', '_')}" if task_id else None

                    # Step 1: Create Done_Signal collection for this task's HC
                    # Ontology: Done_Signal IS_A Local_Collection,
                    #   PART_OF Starsystem_X_Done_Signal_Collections (the category),
                    #   SIGNALS_FOR the task (which PART_OF Deliverable PART_OF ... PART_OF HC)
                    done_signal_name = f"{hc_name}_Done_Signal"
                    try:
                        from carton_mcp.add_concept_tool import add_concept_tool_func
                        # Resolve starsystem from active starlog path (same as GIINT does)
                        ss_name = "Home"
                        # CONNECTS_TO: /tmp/active_starlog_path.txt (read) — written by starlog start_starlog
                        starlog_path_file = Path("/tmp/active_starlog_path.txt")
                        if starlog_path_file.exists():
                            raw = starlog_path_file.read_text().strip()
                            ss_name = Path(raw).name.replace("-", "_").replace(" ", "_").title()
                        done_signal_category = f"Starsystem_{ss_name}_Done_Signal_Collections"

                        rels = [
                            {"relationship": "is_a", "related": ["Local_Collection"]},
                            {"relationship": "part_of", "related": [done_signal_category]},
                            {"relationship": "instantiates", "related": ["Done_Signal_Collection_Category"]},
                        ]
                        if task_concept:
                            rels.append({"relationship": "signals_for", "related": [task_concept]})

                        add_concept_tool_func(
                            done_signal_name,
                            f"Done signal collection for {hc_name}. Agent fills with observations, bugs, and proofs during work. Unverified claim — CE validates before promotion to Completed.",
                            rels,
                            desc_update_mode="append",
                            hide_youknow=True,
                        )
                        logger.info(f"[Memory Recompile] Ensured Done_Signal: {done_signal_name} signals_for={task_concept}")
                    except Exception as e:
                        logger.warning(f"[Memory Recompile] Done_Signal creation failed (non-critical): {e}")

                    # Step 2: active_hypercluster.txt already set by GIINT _ensure_giint_hierarchy_in_carton
                    # Step 3: Recompile MEMORY.md with expanded HC context
                    try:
                        from carton_mcp.substrate_projector import compile_memory_tier
                        compile_result = compile_memory_tier(0, active_hypercluster=hc_name)
                        logger.info(f"[Memory Recompile] MEMORY.md recompiled: {compile_result}")
                    except Exception as e:
                        logger.error(f"[Memory Recompile] compile_memory_tier failed: {e}", exc_info=True)

                    # Step 4: MEMORY.md hot-reloads next turn automatically
                else:
                    logger.warning("[Memory Recompile] No active_hypercluster.txt or no result data after get_next_task")
            except Exception as e:
                logger.error(f"[Memory Recompile] Chain failed (non-critical): {e}", exc_info=True)

        result_dict = {"success": True}
        if narration:
            result_dict["narration"] = narration
        return result_dict

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
            narration = result.get("narration") if isinstance(result, dict) else None
            with open('/tmp/omnisanc_POSTTOOLUSE_COMPLETE.log', 'a') as f:
                f.write(f"{datetime.now()} Completed! tool_name={tool_name}, narration={bool(narration)}\n")
                f.flush()
            if narration:
                print(f"{narration}", file=sys.stderr)
                sys.exit(2)
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
