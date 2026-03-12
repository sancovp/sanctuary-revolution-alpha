#!/usr/bin/env python3
"""
STARSHIP MCP Server - Experiential Captain Identity Bridge

Provides the experiential transformation layer between SEED identity and STARLOG operations.
Handles the narrative journey of adopting the captain persona and preparing for STARLOG missions.
Also manages flight configurations as the captain prepares for their journey.
"""

import logging
import os
import json
from typing import Optional, List, Union
from datetime import datetime
from fastmcp import FastMCP

# Import internal functions from installed starlog_mcp library
from starlog_mcp.starlog_mcp import (
    internal_fly,
    internal_add_flight_config,
    internal_delete_flight_config,
    internal_update_flight_config,
    internal_read_starlog_flight_config_instruction_manual
)

# Import registry function needed by internal functions
from heaven_base.tools.registry_tool import registry_util_func

# Import PayloadDiscovery models
from payload_discovery.core import PayloadDiscovery, PayloadDiscoveryPiece

# Import auto-population
from .auto_populate import auto_populate_defaults

# Import Pydantic for step model
from pydantic import BaseModel, Field

# Simple step model for AI input
class StepInput(BaseModel):
    """
    Step input for knowledge_update.

    Each step must have:
    - title: Short step title (e.g., "Set up OAuth credentials")
    - content: Detailed step instructions (e.g., "1. Go to Google Cloud Console\\n2. Create OAuth 2.0 Client ID")

    Example:
    {"title": "Install dependencies", "content": "Run npm install to install all required packages"}
    """
    title: str = Field(..., description="Step title (required)")
    content: str = Field(..., description="Step instructions/content (required)")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP
mcp = FastMCP("STARSHIP")

@mcp.tool()
def launch_routine(starlog_path: Optional[str] = None) -> str:
    """
    Execute the starship launch routine - experiential transformation into captain persona.
    
    This is the bridge between SEED identity and STARLOG operations. Guides the user through
    adopting the captain persona and preparing for their STARLOG mission.
    
    Args:
        starlog_path: Optional STARLOG project path for narrative enforcement
        
    Returns:
        Launch sequence guidance and captain persona adoption
    """
    logger.info(f"Executing starship launch routine, starlog_path: {starlog_path}")
    
    # Auto-populate default flight configs if needed
    try:
        from pathlib import Path
        heaven_data_dir = os.getenv("HEAVEN_DATA_DIR")
        if not heaven_data_dir:
            logger.warning("HEAVEN_DATA_DIR not set, skipping auto-population")
            return launch_sequence
        registry_path = Path(os.path.join(heaven_data_dir, "registry/starlog_flight_configs_registry.json"))
        if registry_path.exists():
            # Only populate if registry exists (STARLOG is initialized)
            auto_populate_status = auto_populate_defaults()
            logger.info(f"Auto-population status: {auto_populate_status}")
    except Exception as e:
        logger.warning(f"Failed to auto-populate flight configs during launch: {e}", exc_info=True)
    
    # TODO: Add OMNISANC validation here
    # if starlog_path:
    #     validation = omnisanc.validate_sequence(starlog_path, "⭐")
    #     if not validation.allowed:
    #         return validation.error_message
    
    launch_sequence = """⭐ STARPORT PHASE - FLIGHT SELECTION

You're in the STARPORT phase. This is where you browse available flight configs
and select the next waypoint journey for your mission.

## What Just Happened

You either:
- Just plotted a course (mission started)
- Completed a LANDING phase (session reviewed and documented)

Either way, you're now ready to select your next flight.

## What Happens Next

### Step 1: Browse Available Flights

Call `starship.fly()` to see available flight configs:

```python
starship.fly(path="{starlog_path if starlog_path else '/path/to/project'}")
```

This will show:
- Available flight configs organized by category
- Default flight configs (auto-populated)
- Primitives you created during sessions
- Composite flight configs you built

### Step 2: Select and Start a Flight

Once you find the flight config you want, start it with waypoint:

```python
waypoint.start_waypoint_journey(
    config_path="/path/to/flight/config.json",
    starlog_path="{starlog_path if starlog_path else '/path/to/project'}"
)
```

This will:
- Initialize the waypoint journey
- Load the PayloadDiscovery
- Enter SESSION phase
- Guide you through each step

## Session Phase

Once waypoint journey starts:
- Follow the waypoint steps
- Use knowledge_update() to capture learnings
- Call end_starlog() when done
- This returns you to LANDING phase

## Summary

🔹 You are in STARPORT phase
🔹 NEXT: Call fly() to browse available flights
🔹 THEN: Call waypoint.start_waypoint_journey() to begin session
🔹 WORK: Follow waypoints, capture knowledge
🔹 END: Call end_starlog() to enter LANDING phase

The spiral continues: LANDING → STARPORT → SESSION → LANDING → ..."""
    
    # TODO: Add to STARLOG debug diary with ⭐ emoji
    # if starlog_path:
    #     starlog.update_debug_diary(
    #         content=f"⭐ STARSHIP LAUNCH COMPLETE: Captain persona adopted and ready for STARLOG operations",
    #         starlog_path=starlog_path
    #     )
    
    return launch_sequence

@mcp.tool()
def landing_routine(starlog_path: Optional[str] = None) -> str:
    """
    Execute the starship landing routine - transition from captain operations back to base identity.
    
    Provides closure to the captain experience and transitions back to the foundational identity
    established by SEED systems.
    
    Args:
        starlog_path: Optional STARLOG project path for narrative enforcement
        
    Returns:
        Landing sequence guidance and identity transition
    """
    logger.info(f"Executing starship landing routine, starlog_path: {starlog_path}")
    
    # TODO: Add OMNISANC validation here
    # if starlog_path:
    #     validation = omnisanc.validate_sequence(starlog_path, "🛬")
    #     if not validation.allowed:
    #         return validation.error_message
    
    landing_sequence = """🛬 LANDING PHASE - SESSION REVIEW

You've ended your session and entered the LANDING phase. This is where you review
what you captured and document your progress before continuing the mission.

## What Just Happened

Your STARLOG session has ended. Any knowledge you captured during the session using
`knowledge_update()` has been stored as primitive flight configs.

## What Happens Next - 3 Mandatory Steps

The LANDING phase has 3 required steps (OMNISANC enforces this sequence):

### Step 1: landing_routine() ✅ (You just called this)

You're here now. This tool explains the LANDING phase.

### Step 2: session_review() (CALL THIS NEXT)

This will show you:
- All primitives you captured during the session
- How many steps each primitive has
- Composition syntax for combining primitives into larger flight configs

Call it like this:
```
starship.session_review(starlog_path="{starlog_path if starlog_path else '/path/to/project'}")
```

### Step 3: giint.respond() (REQUIRED AFTER session_review)

After session_review, you MUST document this session's progress in the mission QA.

session_review will give you the exact mission_id and instructions for calling
giint.respond() with your session notes.

## After All 3 Steps Complete

Once you've completed landing_routine → session_review → giint.respond, you can:

- **Continue mission**: Call `starship.fly()` to browse flights for next session
- **Complete mission**: Call `complete_mission(mission_id)` to finish

## Summary

🔹 You are in LANDING phase
🔹 NEXT: Call session_review() to see your captured primitives
🔹 THEN: Call giint.respond() to document this session
🔹 THEN: fly() for next session OR complete_mission()

OMNISANC will guide you through each step."""
    
    # TODO: Add to STARLOG debug diary with 🛬 emoji
    # if starlog_path:
    #     starlog.update_debug_diary(
    #         content=f"🛬 STARSHIP LANDING COMPLETE: Mission accomplished, returning to base identity",
    #         starlog_path=starlog_path
    #     )
    
    return landing_sequence

# COURSE MANAGEMENT (OMNISANC CORE INTEGRATION)

@mcp.tool()
def continue_course() -> str:
    """
    Continue the current course after conversation compact or interruption.

    Clears the was_compacted flag and resumes the journey with existing course.
    You still need to call starlog.orient() again to reload project context.

    Returns:
        Continuation confirmation and next steps
    """
    logger.info("Continuing current course after compact/interruption")

    COURSE_STATE_FILE = os.path.join(os.environ["HEAVEN_DATA_DIR"], "omnisanc_core/.course_state")

    try:
        if not os.path.exists(COURSE_STATE_FILE):
            return "❌ No active course found. Use starship.plot_course() to start a new Journey."

        # Read current state
        with open(COURSE_STATE_FILE, 'r') as f:
            course_state = json.load(f)

        if not course_state.get("course_plotted", False):
            return "❌ No active course found. Use starship.plot_course() to start a new Journey."

        # Clear compacted flag and reset oriented
        course_state["was_compacted"] = False
        course_state["oriented"] = False  # Must re-orient after compact

        # Save updated state
        with open(COURSE_STATE_FILE, 'w') as f:
            json.dump(course_state, f, indent=2)

        projects = course_state.get("projects", [])
        project_path = projects[0] if projects else "unknown"
        description = course_state.get("description", "")

        return f"""🔄 COURSE CONTINUED

Project: {project_path}
Mission: {description}

✅ Resuming Journey Mode

Next Step: Call starlog.orient("{project_path}") to reload project context
After orient(), all tools will be available for your work.

🗺️ Your course is active again."""

    except Exception as e:
        logger.error(f"Failed to continue course: {e}", exc_info=True)
        return f"❌ Failed to continue course: {str(e)}"

@mcp.tool()
def get_course_state() -> str:
    """
    Get current OMNISANC course state to see what mode you're in.

    Shows:
    - Current mode (HOME/JOURNEY)
    - Project path(s) if plotted
    - Flight status (fly called, waypoint active)
    - Session status
    - Mission status

    Returns:
        Formatted course state information
    """
    logger.info("Getting current course state")

    COURSE_STATE_FILE = os.path.join(os.environ["HEAVEN_DATA_DIR"], "omnisanc_core/.course_state")

    try:
        if not os.path.exists(COURSE_STATE_FILE):
            return """# 🏠 OMNISANC Course State

**Mode**: HOME
**Course Plotted**: No

You are in HOME mode. Use starship.plot_course() to enter Journey mode."""

        # Read current state
        with open(COURSE_STATE_FILE, 'r') as f:
            course_state = json.load(f)

        # Determine mode
        if not course_state.get("course_plotted", False):
            mode = "HOME"
        else:
            mode = "JOURNEY"

        # Format projects
        projects = course_state.get("projects", [])
        if not projects:
            # Legacy format with single project_path
            projects = [course_state.get("project_path", "unknown")]

        projects_str = "\n".join(f"  - {p}" for p in projects)

        # Build output
        output = [
            "# 🗺️ OMNISANC Course State",
            "",
            f"**Mode**: {mode}",
            f"**Course Plotted**: {course_state.get('course_plotted', False)}",
            f"**Mission**: {course_state.get('description', 'N/A')}",
            "",
            "**Projects**:",
            projects_str,
            "",
            f"**Fly Called**: {course_state.get('fly_called', False)}",
            f"**Flight Selected**: {course_state.get('flight_selected', False)}",
            f"**Last Oriented**: {course_state.get('last_oriented', 'N/A')}",
            f"**Was Compacted**: {course_state.get('was_compacted', False)}",
            "",
            f"**Session Active**: {course_state.get('session_active', False)}",
            f"**Mission Active**: {course_state.get('mission_active', False)}",
        ]

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Failed to get course state: {e}", exc_info=True)
        return f"❌ Failed to read course state: {str(e)}"


@mcp.tool()
def plot_course(
    project_paths: Union[str, List[str]],
    description: str,
    domain: Optional[str] = None,
    subdomain: Optional[str] = None,
    process: Optional[str] = None
) -> str:
    """
    Plot a course for your session - transitions from Sanctuary to Project Mode.

    This sets the current project context and enables full tool access after
    you call starlog.orient() to load the project.

    Args:
        project_paths: Path(s) to STARLOG project(s) you'll be working on.
                       Can be a single string or a list of strings.
        description: Brief description of what you're trying to accomplish
        domain: Domain categorization (e.g., "backend", "frontend", "ml"). Defaults to "HOME"
        subdomain: Subdomain categorization (e.g., "authentication", "api")
        process: Specific process (e.g., "oauth/google", "rest/crud")

    Returns:
        Course confirmation and next steps
    """
    # Normalize to list (backward compatibility)
    if isinstance(project_paths, str):
        projects = [project_paths]
    else:
        projects = project_paths

    logger.info(f"Plotting course: {projects} - {description}")

    # Course state file and history file
    COURSE_STATE_FILE = os.path.join(os.environ["HEAVEN_DATA_DIR"], "omnisanc_core/.course_state")
    COURSE_HISTORY_FILE = os.path.join(os.environ["HEAVEN_DATA_DIR"], "omnisanc_core/.course_history.json")

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(COURSE_STATE_FILE), exist_ok=True)

        # Get current timestamp
        from datetime import datetime
        timestamp = datetime.now().isoformat()

        # Create base mission (auto-capture mission for unstructured work)
        from starsystem.mission import Mission, MissionMetrics, save_mission

        mission_id = f"base_mission_{timestamp.replace(':', '').replace('-', '').replace('.', '_')}"
        base_mission = Mission(
            mission_id=mission_id,
            name="Base Mission",
            description=description,
            domain="base_work",
            subdomain="unstructured",
            session_sequence=[],  # Starts empty, grows via injection
            current_step=0,
            status="active",
            created_at=timestamp,
            started_at=timestamp,
            metrics=MissionMetrics()
        )

        save_mission(base_mission)
        logger.info(f"Created base mission: {mission_id}")

        # Set course state with mission tracking
        course_state = {
            "course_plotted": True,
            "projects": projects,  # List of projects
            "fly_called": False,  # Track if fly() has been called
            "flight_selected": False,  # Track if waypoint journey started
            "last_oriented": None,  # Track which project we're currently in
            "description": description,
            "was_compacted": False,
            "mission_active": True,  # Base mission is active
            "mission_id": mission_id,
            "mission_step": 0,
            "domain": domain or "HOME",  # NEW: Domain categorization (defaults to HOME)
            "subdomain": subdomain,  # NEW: Subdomain categorization
            "process": process  # NEW: Specific process
        }

        with open(COURSE_STATE_FILE, 'w') as f:
            json.dump(course_state, f, indent=2)

        # Update course history
        try:
            if os.path.exists(COURSE_HISTORY_FILE):
                with open(COURSE_HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            else:
                history = {"courses": []}

            # Add new course entry
            history["courses"].append({
                "timestamp": timestamp,
                "projects": projects,  # Store list of projects
                "description": description,
                "ended": False
            })

            # Write updated history
            with open(COURSE_HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)

            logger.info(f"Course history updated: {len(history['courses'])} total courses")

        except Exception as hist_error:
            logger.warning(f"Failed to update course history: {hist_error}", exc_info=True)
            # Don't fail the whole operation if history update fails

        # Format project list for display
        if len(projects) == 1:
            projects_display = f"Project: {projects[0]}"
            orient_instruction = f'Next Step: Call starlog.orient("{projects[0]}") to load project context'
        else:
            projects_display = "Projects:\n" + "\n".join(f"  - {p}" for p in projects)
            orient_instruction = f"Next Step: Call starlog.orient() on one of the projects above to begin work"

        return f"""🗺️ COURSE PLOTTED

{projects_display}
Mission: {description}

🔄 MODE TRANSITION: Home → Journey Mode

{orient_instruction}
After orient(), all tools will be available for your work.

✨ You are now in Journey Mode with defined course."""

    except Exception as e:
        logger.error(f"Failed to plot course: {e}", exc_info=True)
        return f"❌ Failed to plot course: {str(e)}"

# FLIGHT CONFIGURATION TOOLS
# These tools manage the captain's flight configurations and mission planning

# TODO: FUTURE MODE INTEGRATION
# =============================
# When MODE system is fully implemented, enhance fly() to:
# 1. Mode-Based Flight Config Filtering:
#    - PLANNING Mode: Show only planning-oriented flight configs
#      (project_design, architecture_planning, requirement_gathering, etc.)
#    - EXECUTION Mode: Show only execution-oriented flight configs  
#      (debugging_methodology, feature_implementation, testing_workflow, etc.)
#    - FREESTYLE Mode: Show all flight configs (current behavior)
# 2. Mode Integration Flow:
#    - Captain sets mode in STARSHIP (planning/execution/freestyle)
#    - fly() automatically filters available flight configs by mode
#    - Clear separation of "what kind of mission" (mode) vs "specific workflow" (flight config)
# 3. Enhanced UX:
#    - Mode indicator in flight config display
#    - Mode-specific guidance and recommendations
#    - Clear workflow: set_mode() → fly() → select relevant flight config
# 4. GIINT Integration:
#    - Mode determines which GIINT tools are emphasized
#    - Clear guidance on when to use giint.respond() based on mode
#    - Mode-specific capture triggers (planning discoveries vs execution insights)
# Implementation Strategy:
# - Add mode parameter (optional, defaults to current behavior)
# - Integrate with GIINT mode system for automatic mode detection
# - Filter flight configs by mode categories when mode is specified
# - Maintain backward compatibility with current unfiltered behavior
# This will make STARSHIP the true coordination layer between GIINT project management
# and STARLOG mission execution, with MODE as the bridge connecting all systems.

@mcp.tool()
def fly(path: str, page: int = None, category: str = None, this_project_only: bool = False, search: str = None, show_all: bool = False) -> str:
    """
    Browse and search flight configurations with pagination and categories.

    The captain's primary interface for viewing available flight configurations
    and mission templates.

    Args:
        path: STARLOG project path
        page: Page number for pagination (when category is specified)
        category: Category to filter by (shows categories if None)
        this_project_only: Whether to filter to current project only
        search: Search string to find flights by name/description
        show_all: If True, show all flights in flat list (skip category view)

    Returns:
        Flight configuration display or category listing
    """
    return internal_fly(path, page, category, this_project_only, search, show_all)

@mcp.tool()
def add_flight_config(path: str, name: str, config_data: dict, category: str = "general") -> str:
    """
    Create new flight config with validation.
    
    Captain's tool for defining new mission configurations.
    
    Args:
        path: STARLOG project path
        name: Flight config name (must end with '_flight_config')
        config_data: Configuration data including work_loop_subchain
        category: Category for organizing configs
        
    Returns:
        Success/failure message
    """
    return internal_add_flight_config(path, name, config_data, category)

@mcp.tool()
def delete_flight_config(path: str, name: str) -> str:
    """
    Remove flight config.
    
    Captain's tool for removing obsolete mission configurations.
    
    Args:
        path: STARLOG project path
        name: Flight config name to delete
        
    Returns:
        Success/failure message
    """
    return internal_delete_flight_config(path, name)

@mcp.tool()
def update_flight_config(path: str, name: str, config_data: dict) -> str:
    """
    Modify existing flight config.
    
    Captain's tool for updating mission configurations.
    
    Args:
        path: STARLOG project path
        name: Flight config name to update
        config_data: New configuration data
        
    Returns:
        Success/failure message
    """
    return internal_update_flight_config(path, name, config_data)

@mcp.tool()
def populate_default_flight_configs() -> str:
    """
    Auto-populate default STARSHIP flight configurations.
    
    This seeds the essential meta flight configs that help users create their own
    flight configurations and develop MCPs systematically.
    
    Returns:
        Status message about populated configs
    """
    logger.info("Auto-populating default STARSHIP flight configs...")
    return auto_populate_defaults()

@mcp.tool()
def read_starlog_flight_config_instruction_manual() -> str:
    """
    Show flight config schema, examples, and usage guide.

    Captain's reference manual for understanding flight configurations.

    Returns:
        Complete flight config instruction manual
    """
    return internal_read_starlog_flight_config_instruction_manual()

# STARPORT KNOWLEDGE SYSTEM (Phase 2)

@mcp.tool()
def get_knowledge_update_help() -> str:
    """
    Get instructions and schema for using knowledge_update during sessions.

    Call this when you need to capture knowledge but aren't sure about the format.

    Returns:
        Complete guide to using knowledge_update with StepInput schema
    """
    return """
📚 KNOWLEDGE UPDATE HELP

## Purpose
Capture domain-specific knowledge during your session as a primitive flight config.
Each knowledge capture creates a multi-step PayloadDiscovery that can be composed
into larger flight configs later.

## StepInput Schema

Each step requires exactly TWO fields:

```json
{
  "title": "Short descriptive title",
  "content": "Detailed step instructions"
}
```

### Field Requirements:
- **title** (required): Brief step title (e.g., "Set up OAuth credentials")
- **content** (required): Detailed instructions for this step (e.g., "1. Go to Google Cloud Console\\n2. Create OAuth 2.0 Client ID...")

### ❌ Common Mistakes:
- Missing title or content field → Validation error
- Using other field names → Validation error
- Empty strings → Not recommended

## Usage Examples

### Single Step:
```python
knowledge_update(
    title="Google OAuth Setup Guide",
    steps=[
        {
            "title": "Create OAuth credentials",
            "content": "1. Go to Google Cloud Console\\n2. Navigate to APIs & Services\\n3. Create OAuth 2.0 Client ID"
        }
    ],
    subdomain="authentication",
    process="oauth/google",
    starlog_path="/path/to/project"
)
```

### Multiple Steps:
```python
knowledge_update(
    title="Complete Authentication Flow",
    steps=[
        {
            "title": "Install dependencies",
            "content": "Run: npm install passport passport-google-oauth20"
        },
        {
            "title": "Configure OAuth credentials",
            "content": "1. Create .env file\\n2. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
        },
        {
            "title": "Implement callback route",
            "content": "Create /auth/google/callback endpoint to handle OAuth response"
        }
    ],
    subdomain="authentication",
    process="oauth/google",
    starlog_path="/path/to/project"
)
```

## What Happens After Calling

1. ✅ Creates PayloadDiscovery with your steps
2. ✅ Each step becomes a PayloadDiscoveryPiece
3. ✅ Stores PD in starport_pd_registry
4. ✅ Creates primitive flight config pointing to PD file
5. ✅ Links to current session in starport_session_knowledge
6. ✅ Available for composition in session_review()

## During Session Review

When you call `session_review()` after ending your session, you'll see all
captured primitives with step counts. You can then compose them into larger
flight configs using `add_flight_config()`.

## Required Context

- Must have active STARLOG session (call `starlog.start_starlog()` first)
- Must have active course (call `starship.plot_course()` first)
- Domain comes from course_state, you provide subdomain/process

## Parameters

- **title**: Overall title for this knowledge capture
- **steps**: List of step objects (each with title and content)
- **subdomain**: Specific subdomain (e.g., "authentication", "api", "database")
- **process**: Specific process (e.g., "oauth/google", "rest/crud", "postgres/setup")
- **starlog_path**: Path to your STARLOG project

## Tips

- Keep each step focused on ONE specific task
- Use clear, actionable titles
- Include enough detail in content so future-you understands
- Group related steps into a single knowledge_update call
- Multiple captures per session is fine - they'll all show in session_review()
"""

@mcp.tool()
def knowledge_update(
    title: str,
    capture_type: str,
    subdomain: str,
    process: str,
    starlog_path: str,
    # For skills:
    category: Optional[str] = None,
    content: Optional[str] = None,
    # For flights:
    steps: Optional[List[StepInput]] = None,
) -> str:
    """
    Capture knowledge during session as skill or flight config.

    Integrated with complexity ladder:
    - capture_type="skill" → Creates skill via SkillManager
    - capture_type="flight" → Creates primitive flight config (original behavior)

    SKILL CATEGORIES:
    - understand: Concepts, patterns, "how X works"
    - preflight: Context needed before tasks, decision frameworks
    - single_turn_process: One-shot actions with immediate results

    Args:
        title: Overall title of the knowledge capture
        capture_type: "skill" or "flight"
        subdomain: Subdomain (e.g., "authentication")
        process: Process (e.g., "oauth/google")
        starlog_path: STARLOG project path
        category: For skills - "understand", "preflight", or "single_turn_process"
        content: For skills - SKILL.md body content
        steps: For flights - List of StepInput with title/content

    Returns:
        Confirmation with skill or flight info
    """
    # Validate capture_type
    if capture_type not in ("skill", "flight"):
        return f"❌ Invalid capture_type: {capture_type}. Must be 'skill' or 'flight'."

    # Validate required fields based on capture_type
    if capture_type == "skill":
        if not content:
            return "❌ content is required for skill capture."
        if not category:
            return "❌ category is required for skill capture (understand/preflight/single_turn_process)."
        if category not in ("understand", "preflight", "single_turn_process"):
            return f"❌ Invalid category: {category}. Must be understand/preflight/single_turn_process."
    elif capture_type == "flight":
        if not steps:
            return "❌ steps is required for flight capture."

    logger.info(f"Creating knowledge_update {capture_type}: {title}")

    try:
        # 1. Get active session_id from STARLOG
        from starlog_mcp.starlog import Starlog
        starlog = Starlog()
        project_name = starlog._get_project_name_from_path(starlog_path)

        # Find active session (one without end_timestamp)
        starlog_data = starlog._get_registry_data(project_name, "starlog")
        session_id = None
        for sid, sdata in starlog_data.items():
            if sdata.get("end_timestamp") is None:
                session_id = sid
                break

        if not session_id:
            return "❌ No active STARLOG session. Call starlog.start_starlog() first."

        # 2. Read course state for domain
        COURSE_STATE_FILE = os.path.join(os.environ["HEAVEN_DATA_DIR"], "omnisanc_core/.course_state")
        if not os.path.exists(COURSE_STATE_FILE):
            return "❌ No active course. Use starship.plot_course() first."

        with open(COURSE_STATE_FILE, 'r') as f:
            course_state = json.load(f)

        domain = course_state.get("domain", "HOME")

        # 3. Generate IDs
        import uuid
        capture_id = f"{session_id}_{uuid.uuid4().hex[:8]}"

        # BRANCH: Skill creation
        if capture_type == "skill":
            from skill_manager.core import SkillManager
            sm = SkillManager()

            # Generate skill name from title
            safe_name = title.lower().replace(" ", "-").replace("/", "-").replace("_", "-")[:64]

            # Create skill
            sm.create_skill(
                name=safe_name,
                domain=domain,
                content=content,
                what=title,
                when=f"When you need to understand {subdomain}/{process}",
                subdomain=subdomain,
                category=category
            )

            # Store session knowledge link
            session_knowledge = {
                "session_id": session_id,
                "skill_name": safe_name,
                "title": title,
                "capture_type": "skill",
                "category": category,
                "domain": domain,
                "subdomain": subdomain,
                "process": process,
                "timestamp": json.dumps({"$date": datetime.now().isoformat()})
            }

            registry_util_func("add", registry_name="starport_session_knowledge",
                              key=capture_id, value_dict=session_knowledge)

            logger.info(f"Created skill and linked to session {session_id}: {capture_id}")

            return f"""✅ Skill Captured: {safe_name}

Session: {session_id}
Capture Type: skill
Category: {category}

Domain: {domain}
Subdomain: {subdomain}
Process: {process}

Title: {title}

Created skill in global catalog. Equip with: equip.exec {{"name": "{safe_name}"}}"""

        # BRANCH: Flight creation (original behavior)
        pd_id = f"pd_{uuid.uuid4().hex[:8]}"

        # 4. Create PayloadDiscoveryPiece objects from StepInput
        pieces = []
        for i, step in enumerate(steps):
            piece = PayloadDiscoveryPiece(
                sequence_number=i,
                filename=f"step_{i+1}.md",
                title=step.title,
                content=step.content,
                piece_type="instruction",
                dependencies=[]
            )
            pieces.append(piece)

        # 5. Create PayloadDiscovery
        pd = PayloadDiscovery(
            domain=f"{domain}_{subdomain}_{process}",
            version="v1",
            description=title,
            root_files=pieces,
            entry_point="step_1.md"
        )

        # 6. Save PD as JSON file
        pd_dir = os.path.join(os.environ["HEAVEN_DATA_DIR"], "starport_knowledge/pd_files")
        os.makedirs(pd_dir, exist_ok=True)
        pd_file = os.path.join(pd_dir, f"{pd_id}.json")

        with open(pd_file, 'w') as f:
            f.write(pd.to_json())

        logger.info(f"Created PD file: {pd_file}")

        # Store PD in registry for session knowledge tracking
        registry_util_func("add", registry_name="starport_pd_registry", key=pd_id, value_dict=json.loads(pd.to_json()))
        logger.info(f"Stored PD in registry: {pd_id}")

        # 7. Create primitive flight config
        safe_title = title.lower().replace(" ", "_").replace("/", "_")[:30]
        primitive_name = f"{safe_title}_{pd_id}_primitive_flight_config"

        config_data = {
            "description": f"STARPORT Knowledge: {title}",
            "work_loop_subchain": pd_file
        }

        result = internal_add_flight_config(
            path=starlog_path,
            name=primitive_name,
            config_data=config_data,
            category=f"{domain}/{subdomain}/{process}" if subdomain and process else domain
        )

        if "✅" not in result:
            return f"❌ Failed to create flight config: {result}"

        # 8. Store session knowledge link in registry
        session_knowledge = {
            "session_id": session_id,
            "pd_id": pd_id,
            "flight_config_name": primitive_name,
            "title": title,
            "step_count": len(steps),
            "domain": domain,
            "subdomain": subdomain,
            "process": process,
            "timestamp": json.dumps({"$date": datetime.now().isoformat()})
        }

        registry_util_func("add", registry_name="starport_session_knowledge",
                          key=capture_id, value_dict=session_knowledge)

        logger.info(f"Linked to session {session_id}: {capture_id}")

        return f"""✅ Knowledge Captured: {primitive_name}

Session: {session_id}
PD ID: {pd_id}

Domain: {domain}
Subdomain: {subdomain}
Process: {process}

Title: {title}
Steps: {len(steps)}

Stored in registry and created primitive flight config."""

    except Exception as e:
        logger.error(f"Failed to create knowledge_update: {e}", exc_info=True)
        return f"❌ Failed to create knowledge_update: {str(e)}"

@mcp.tool()
def session_review(starlog_path: str, got_compacted: bool = False) -> str:
    """
    Review knowledge captured during current session and prompt for composition.

    REGISTRY FLOW:
    1. Get active session_id from STARLOG
    2. Query starport_session_knowledge for this session's captures
    3. Show primitives created
    4. Prompt with add_flight_config() syntax for composition

    Args:
        starlog_path: STARLOG project path
        got_compacted: Whether conversation was compacted (affects confidence)

    Returns:
        Review prompt with primitives and composition instructions
    """
    logger.info(f"Running session_review for {starlog_path}")

    try:
        # 1. Get active session_id from STARLOG and mission_id from course_state
        from starlog_mcp.starlog import Starlog
        from heaven_base.registry.registry_service import RegistryService

        starlog = Starlog()
        project_name = starlog._get_project_name_from_path(starlog_path)

        # Find active session
        starlog_data = starlog._get_registry_data(project_name, "starlog")
        session_id = None
        for sid, sdata in starlog_data.items():
            if sdata.get("end_timestamp") is None:
                session_id = sid
                break

        if not session_id:
            return "❌ No active STARLOG session found."

        # Get mission_id from course_state
        COURSE_STATE_FILE = os.path.join(os.environ["HEAVEN_DATA_DIR"], "omnisanc_core/.course_state")
        mission_id = None
        if os.path.exists(COURSE_STATE_FILE):
            with open(COURSE_STATE_FILE, 'r') as f:
                course_state = json.load(f)
                mission_id = course_state.get("mission_id")

        if not mission_id:
            return "❌ No active mission. session_review requires active mission context."

        # 2. Query starport_session_knowledge for this session's captures
        service = RegistryService()
        all_captures = service.get_all("starport_session_knowledge")

        if not all_captures:
            return f"""🔍 STARPORT SESSION REVIEW

Mission: {mission_id}
Session: {session_id}
Status: No knowledge captures during this session.

You can still compose existing flight configs using:
starship.add_flight_config(path, name, {{"work_loop_subchain": ["config1", "config2"]}})

---

## 📝 REQUIRED NEXT STEP: Document This Session

Even without primitives, you MUST call giint.respond() to document this session.

Call: giint.respond(qa_id="{mission_id}", ..., simple_response_string="Session notes...")

After giint.respond() completes:
- Call starship.fly() to continue mission
- OR call complete_mission(mission_id="{mission_id}") to finish"""

        # Filter captures for this session
        session_captures = {}
        for capture_id, capture_data in all_captures.items():
            if capture_data.get("session_id") == session_id:
                session_captures[capture_id] = capture_data

        if not session_captures:
            return f"""🔍 STARPORT SESSION REVIEW

Mission: {mission_id}
Session: {session_id}
Status: No knowledge captures during this session.

You can still compose existing flight configs using:
starship.add_flight_config(path, name, {{"work_loop_subchain": ["config1", "config2"]}})

---

## 📝 REQUIRED NEXT STEP: Document This Session

Even without primitives, you MUST call giint.respond() to document this session.

Call: giint.respond(qa_id="{mission_id}", ..., simple_response_string="Session notes...")

After giint.respond() completes:
- Call starship.fly() to continue mission
- OR call complete_mission(mission_id="{mission_id}") to finish"""

        # 3. Format primitives created
        primitives_list = []
        for capture_id, capture_data in session_captures.items():
            primitives_list.append({
                "name": capture_data.get("flight_config_name"),
                "title": capture_data.get("title"),
                "step_count": capture_data.get("step_count", 1),
                "domain": capture_data.get("domain"),
                "subdomain": capture_data.get("subdomain"),
                "process": capture_data.get("process")
            })

        # Build review output
        output = [
            "🔍 STARPORT SESSION REVIEW",
            "",
            f"Mission: {mission_id}",
            f"Session: {session_id}",
            f"Compacted: {got_compacted}",
            f"Confidence: {'Low (compacted)' if got_compacted else 'High'}",
            "",
            f"📦 Primitives Created: {len(primitives_list)}",
            ""
        ]

        for i, prim in enumerate(primitives_list, 1):
            output.append(f"{i}. **{prim['title']}**")
            output.append(f"   Flight Config: `{prim['name']}`")
            output.append(f"   Steps: {prim['step_count']}")
            output.append(f"   Domain: {prim['domain']}/{prim['subdomain']}/{prim['process']}")
            output.append("")

        # TODO: Future enhancement - integrate treeshell navigation logic here
        # Add interactive interface for deciding WHEN each primitive vs composite
        # gets used in a mission. This will provide mission-level orchestration
        # where users can define conditional logic and sequencing for flight configs.

        output.extend([
            "🔗 Composition Options:",
            "",
            "To compose primitives into a composite flight config:",
            "",
            "```python",
            "starship.add_flight_config(",
            f'    path="{starlog_path}",',
            '    name="my_composite_flight_config",',
            '    config_data={',
            '        "description": "Composite workflow description",',
            '        "work_loop_subchain": [',
        ])

        # Add primitive names as references
        for prim in primitives_list:
            output.append(f'            "{prim["name"]}",')

        output.extend([
            '        ]',
            '    },',
            f'    category="{primitives_list[0]["domain"]}/{primitives_list[0]["subdomain"]}/{primitives_list[0]["process"]}"',
            ')',
            "```",
            "",
            "The flight config system will resolve these references when executing the composite.",
            "",
            "---",
            "",
            "## 📝 REQUIRED NEXT STEP: Document This Session",
            "",
            "You MUST now call giint.respond() to document this session's progress in the mission QA.",
            "",
            "Call it like this:",
            "```python",
            "giint.respond(",
            f'    qa_id="{mission_id}",',
            '    user_prompt_description="Session review for [describe what you did]",',
            '    one_liner="Brief summary of session outcomes",',
            '    key_tags=["session_review", "domain_tag", "work_tag"],',
            '    involved_files=["file1.py", "file2.py"],  # Files you worked on',
            '    project_id="project_name",',
            '    feature="feature_name",',
            '    component="component_name",',
            '    deliverable="deliverable_name",',
            '    subtask="subtask_name",',
            '    task="task_name",',
            '    workflow_id="workflow_name",',
            '    simple_response_string="""',
            '    Your session notes here:',
            '    - What you accomplished',
            '    - Key decisions made',
            '    - Primitives created and why',
            '    - Next steps for mission',
            '    """',
            ')',
            "```",
            "",
            "## After giint.respond() Completes",
            "",
            "You can then:",
            "- **Continue mission**: Call `starship.fly()` to select next flight",
            "- **Complete mission**: Call `complete_mission(mission_id=\"" + mission_id + "\")` to finish",
            "",
            "OMNISANC will enforce this sequence."
        ])

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Failed session_review: {e}", exc_info=True)
        return f"❌ Failed session_review: {str(e)}"

def main():
    """Main entry point for the Starship MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()