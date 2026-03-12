"""GIINT integration operations - INTERACTIVE project building.

Each paia-builder spec field maps to giint deliverables/tasks.
Build projects interactively, not auto-generated garbage.

NOTE: giint integration is OPTIONAL. Set PAIA_ENABLE_GIINT=1 to enable.
Currently disabled by default due to giint library issues:
- Single global projects.json (not per-project)
- Task status updates not working reliably
- Unclear integration purpose
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os

# Feature flag - disabled by default
GIINT_ENABLED = os.environ.get("PAIA_ENABLE_GIINT", "0") == "1"

if GIINT_ENABLED:
    try:
        from llm_intelligence.projects import (
            create_project as giint_create_project,
            add_feature_to_project as giint_add_feature,
            add_component_to_feature as giint_add_component,
            add_deliverable_to_component as giint_add_deliverable,
            add_task_to_deliverable as giint_add_task,
            update_task_status as giint_update_task,
            add_spec_to_component as giint_add_spec_to_component,
            add_spec_to_deliverable as giint_add_spec_to_deliverable,
        )
        GIINT_AVAILABLE = True
    except ImportError:
        GIINT_AVAILABLE = False
else:
    GIINT_AVAILABLE = False


# =============================================================================
# PROJECT INITIALIZATION
# =============================================================================

def init_giint_project(name: str, project_dir: str, features: Optional[List[str]] = None) -> Dict[str, Any]:
    """Initialize GIINT project with specified features.

    Args:
        name: Project name (PAIA name)
        project_dir: Project directory path
        features: List of feature names. If None, uses default component types.
    """
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    result = giint_create_project(project_id=name, project_dir=project_dir, starlog_path=project_dir)
    if "error" in result:
        return result

    # Default features = component types
    if features is None:
        from .constants import COMPONENT_TYPES
        features = COMPONENT_TYPES

    for feat in features:
        feat_result = giint_add_feature(name, feat)
        if "error" in feat_result:
            return {"success": False, "error": f"Failed to add feature {feat}"}

    return {"success": True, "message": f"GIINT project '{name}' created with features: {features}"}


# =============================================================================
# COMPONENT CREATION (just creates component, NO auto-deliverables)
# =============================================================================

def add_component(paia_name: str, feature: str, comp_name: str) -> Dict[str, Any]:
    """Add a component to a feature. NO auto-generated deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    result = giint_add_component(paia_name, feature, comp_name)
    if "error" in result:
        return result

    return {"success": True, "message": f"Component '{comp_name}' added to feature '{feature}'"}


# =============================================================================
# DELIVERABLE CREATION (each spec field = a deliverable)
# =============================================================================

def add_deliverable(
    paia_name: str,
    feature: str,
    comp_name: str,
    deliverable_name: str,
    task_id: Optional[str] = None,
    agent_id: str = "paia-builder"
) -> Dict[str, Any]:
    """Add a deliverable to a component with an initial task.

    Args:
        paia_name: PAIA/project name
        feature: Feature name (e.g., "skills", "mcps")
        comp_name: Component name
        deliverable_name: Deliverable name (e.g., "skill_md", "reference_md")
        task_id: Task ID (defaults to "create_{deliverable_name}")
        agent_id: Agent assigned to this task
    """
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    # Add deliverable
    del_result = giint_add_deliverable(paia_name, feature, comp_name, deliverable_name)
    if "error" in del_result:
        return del_result

    # Add initial task
    if task_id is None:
        task_id = f"create_{deliverable_name}"

    task_result = giint_add_task(
        project_id=paia_name,
        feature_name=feature,
        component_name=comp_name,
        deliverable_name=deliverable_name,
        task_id=task_id,
        is_human_only_task=False,
        agent_id=agent_id
    )
    if "error" in task_result:
        return task_result

    return {"success": True, "message": f"Deliverable '{deliverable_name}' added with task '{task_id}'"}


def add_task(
    paia_name: str,
    feature: str,
    comp_name: str,
    deliverable_name: str,
    task_id: str,
    is_human_only: bool = False,
    agent_id: Optional[str] = "paia-builder",
    human_name: Optional[str] = None
) -> Dict[str, Any]:
    """Add a task to a deliverable."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    return giint_add_task(
        project_id=paia_name,
        feature_name=feature,
        component_name=comp_name,
        deliverable_name=deliverable_name,
        task_id=task_id,
        is_human_only_task=is_human_only,
        agent_id=agent_id if not is_human_only else None,
        human_name=human_name if is_human_only else None
    )


def complete_task(
    paia_name: str,
    feature: str,
    comp_name: str,
    deliverable_name: str,
    task_id: str
) -> Dict[str, Any]:
    """Mark a task as done."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    return giint_update_task(
        project_id=paia_name,
        feature_name=feature,
        component_name=comp_name,
        deliverable_name=deliverable_name,
        task_id=task_id,
        is_done=True,
        is_blocked=False,
        blocked_description=None,
        is_ready=True
    )


# =============================================================================
# SPEC ATTACHMENT (link paia-builder spec JSON to giint component)
# =============================================================================

def attach_spec_to_component(
    paia_name: str,
    feature: str,
    comp_name: str,
    spec_data: Dict[str, Any],
    spec_dir: str
) -> Dict[str, Any]:
    """Save spec as JSON and attach to giint component.

    Args:
        paia_name: PAIA/project name
        feature: Feature name
        comp_name: Component name
        spec_data: Pydantic model dict (from spec.model_dump())
        spec_dir: Directory to save spec JSON
    """
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    # Save spec as JSON
    spec_path = Path(spec_dir) / feature / f"{comp_name}_spec.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(spec_data, indent=2, default=str))

    # Attach to giint
    result = giint_add_spec_to_component(
        project_id=paia_name,
        feature_name=feature,
        component_name=comp_name,
        spec_file_path=str(spec_path)
    )

    if "error" in result:
        return result

    return {"success": True, "spec_path": str(spec_path)}


# =============================================================================
# SKILL-SPECIFIC HELPERS
# =============================================================================

def add_skill_deliverables(paia_name: str, skill_name: str) -> Dict[str, Any]:
    """Add standard skill deliverables (skill_md, reference_md, etc).

    Called AFTER add_component. Adds the deliverables that every skill has.
    """
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "skills"
    deliverables = [
        ("skill_md", "create_skill_md"),
        ("reference_md", "create_reference_md"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, skill_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Skill deliverables added for '{skill_name}'"}


def add_skill_resource_deliverable(
    paia_name: str,
    skill_name: str,
    resource_name: str
) -> Dict[str, Any]:
    """Add a resource deliverable to a skill."""
    return add_deliverable(
        paia_name, "skills", skill_name,
        f"resource_{resource_name}",
        f"create_resource_{resource_name}"
    )


def add_skill_script_deliverable(
    paia_name: str,
    skill_name: str,
    script_name: str
) -> Dict[str, Any]:
    """Add a script deliverable to a skill."""
    return add_deliverable(
        paia_name, "skills", skill_name,
        f"script_{script_name}",
        f"create_script_{script_name}"
    )


def add_skill_template_deliverable(
    paia_name: str,
    skill_name: str,
    template_name: str
) -> Dict[str, Any]:
    """Add a template deliverable to a skill."""
    return add_deliverable(
        paia_name, "skills", skill_name,
        f"template_{template_name}",
        f"create_template_{template_name}"
    )


# =============================================================================
# MCP-SPECIFIC HELPERS
# =============================================================================

def add_mcp_deliverables(paia_name: str, mcp_name: str) -> Dict[str, Any]:
    """Add standard MCP deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "mcps"
    deliverables = [
        ("onion_utils", "create_utils_py"),
        ("onion_core", "create_core_py"),
        ("mcp_server", "create_mcp_server_py"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, mcp_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"MCP deliverables added for '{mcp_name}'"}


def add_mcp_tool_deliverable(
    paia_name: str,
    mcp_name: str,
    tool_name: str
) -> Dict[str, Any]:
    """Add a tool deliverable to an MCP."""
    return add_deliverable(
        paia_name, "mcps", mcp_name,
        f"tool_{tool_name}",
        f"create_tool_{tool_name}"
    )


# =============================================================================
# HOOK-SPECIFIC HELPERS
# =============================================================================

def add_hook_deliverables(paia_name: str, hook_name: str) -> Dict[str, Any]:
    """Add standard hook deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "hooks"
    deliverables = [
        ("script", "create_hook_script"),
        ("config", "configure_hook"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, hook_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Hook deliverables added for '{hook_name}'"}


# =============================================================================
# COMMAND-SPECIFIC HELPERS
# =============================================================================

def add_command_deliverables(paia_name: str, cmd_name: str) -> Dict[str, Any]:
    """Add standard slash command deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "commands"
    deliverables = [
        ("prompt_content", "write_prompt_content"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, cmd_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Command deliverables added for '{cmd_name}'"}


# =============================================================================
# AGENT-SPECIFIC HELPERS
# =============================================================================

def add_agent_deliverables(paia_name: str, agent_name: str) -> Dict[str, Any]:
    """Add standard agent deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "agents"
    deliverables = [
        ("system_prompt", "write_system_prompt"),
        ("config", "configure_agent"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, agent_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Agent deliverables added for '{agent_name}'"}


# =============================================================================
# PERSONA-SPECIFIC HELPERS
# =============================================================================

def add_persona_deliverables(paia_name: str, persona_name: str) -> Dict[str, Any]:
    """Add standard persona deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "personas"
    deliverables = [
        ("frame", "write_frame"),
        ("config", "configure_bundles"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, persona_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Persona deliverables added for '{persona_name}'"}


# =============================================================================
# PLUGIN-SPECIFIC HELPERS
# =============================================================================

def add_plugin_deliverables(paia_name: str, plugin_name: str) -> Dict[str, Any]:
    """Add standard plugin deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "plugins"
    deliverables = [
        ("manifest", "create_plugin_manifest"),
        ("structure", "create_plugin_structure"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, plugin_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Plugin deliverables added for '{plugin_name}'"}


# =============================================================================
# FLIGHT-SPECIFIC HELPERS
# =============================================================================

def add_flight_deliverables(paia_name: str, flight_name: str) -> Dict[str, Any]:
    """Add standard flight deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "flights"
    deliverables = [
        ("config", "create_flight_config"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, flight_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Flight deliverables added for '{flight_name}'"}


def add_flight_step_deliverable(
    paia_name: str,
    flight_name: str,
    step_number: int
) -> Dict[str, Any]:
    """Add a step deliverable to a flight."""
    return add_deliverable(
        paia_name, "flights", flight_name,
        f"step_{step_number}",
        f"create_step_{step_number}"
    )


# =============================================================================
# METASTACK-SPECIFIC HELPERS
# =============================================================================

def add_metastack_deliverables(paia_name: str, metastack_name: str) -> Dict[str, Any]:
    """Add standard metastack deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "metastacks"
    deliverables = [
        ("model_file", "create_model_file"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, metastack_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Metastack deliverables added for '{metastack_name}'"}


def add_metastack_field_deliverable(
    paia_name: str,
    metastack_name: str,
    field_name: str
) -> Dict[str, Any]:
    """Add a field deliverable to a metastack."""
    return add_deliverable(
        paia_name, "metastacks", metastack_name,
        f"field_{field_name}",
        f"define_field_{field_name}"
    )


# =============================================================================
# AUTOMATION-SPECIFIC HELPERS
# =============================================================================

def add_automation_deliverables(paia_name: str, automation_name: str) -> Dict[str, Any]:
    """Add standard automation deliverables."""
    if not GIINT_AVAILABLE:
        return {"success": False, "error": "GIINT not available"}

    feature = "automations"
    deliverables = [
        ("workflow", "create_workflow"),
        ("webhook", "configure_webhook"),
    ]

    for del_name, task_id in deliverables:
        result = add_deliverable(paia_name, feature, automation_name, del_name, task_id)
        if "error" in result:
            return result

    return {"success": True, "message": f"Automation deliverables added for '{automation_name}'"}


# =============================================================================
# LEGACY COMPAT (to be removed)
# =============================================================================

def create_giint_component(paia_name: str, comp_type: str, comp_name: str) -> Dict[str, Any]:
    """DEPRECATED: Use add_component + add_*_deliverables instead."""
    # Just add the component, no auto-generated tier garbage
    return add_component(paia_name, comp_type, comp_name)


def update_giint_task_done(paia_name: str, comp_type: str, comp_name: str, tier_name: str) -> Dict[str, Any]:
    """DEPRECATED: Use complete_task instead."""
    return complete_task(paia_name, comp_type, comp_name, tier_name, f"reach_{tier_name}")
