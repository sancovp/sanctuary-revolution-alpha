"""PAIA Builder Utils - Re-exports from util_deps.

Thin layer importing from decomposed modules.
"""

# Constants
from .util_deps.constants import COMPONENT_TYPES, TIER_NAMES, COMPONENT_TYPE_MAP

# Storage
from .util_deps.storage import (
    get_storage_dir, get_config_path, get_paia_path,
    load_current_name, save_current_name, load_paia, list_all_paias, delete_paia,
)

# Project structure
from .util_deps.project import (
    init_project_structure, generate_component_doc, generate_claude_md,
)

# GIINT - Interactive project building
from .util_deps.giint_ops import (
    GIINT_AVAILABLE, init_giint_project,
    # Core operations
    add_component, add_deliverable, add_task, complete_task, attach_spec_to_component,
    # Skill helpers
    add_skill_deliverables, add_skill_resource_deliverable, add_skill_script_deliverable, add_skill_template_deliverable,
    # MCP helpers
    add_mcp_deliverables, add_mcp_tool_deliverable,
    # Hook helpers
    add_hook_deliverables,
    # Command helpers
    add_command_deliverables,
    # Agent helpers
    add_agent_deliverables,
    # Persona helpers
    add_persona_deliverables,
    # Plugin helpers
    add_plugin_deliverables,
    # Flight helpers
    add_flight_deliverables, add_flight_step_deliverable,
    # Metastack helpers
    add_metastack_deliverables, add_metastack_field_deliverable,
    # Automation helpers
    add_automation_deliverables,
    # Legacy compat (deprecated)
    create_giint_component, update_giint_task_done,
)

# Components
from .util_deps.components import (
    find_component, get_all_components, component_summary, golden_summary,
)

# Tier/Golden
from .util_deps.tier_golden import (
    get_next_tier, advance_component_tier, set_component_tier,
    get_next_golden, advance_golden, regress_golden,
)

# GEAR
from .util_deps.gear_ops import recalculate_points, sync_gear, update_gear_dimension, log_experience

# Validation
from .util_deps.validation import validate_system_prompt, render_system_prompt

# Creators
from .util_deps.creators import (
    create_skill_spec, create_mcp_spec, create_hook_spec, create_command_spec,
    create_agent_spec, create_persona_spec, create_plugin_spec, create_flight_spec,
    create_metastack_spec, create_giint_blueprint_spec, create_operadic_flow_spec,
    create_frontend_integration_spec, create_automation_spec,
    create_agent_gan_spec, create_agent_duo_spec,
    create_system_prompt_spec, create_system_prompt_config, create_system_prompt_section,
)

# PAIA ops
from .util_deps.paia_ops import create_paia, fork_paia, fork_agent, publish_paia

# YOUKNOW ops
from .util_deps.youknow_ops import register_component_in_youknow, sync_to_youknow


# Additional helpers that compose util_deps functions
from pathlib import Path
from datetime import datetime
from typing import Optional
from .models import PAIA, GoldenStatus
from .util_deps.components import find_component as _find_component


def save_paia(storage_dir: Path, paia: PAIA) -> None:
    """Save PAIA to JSON file with sync_gear (E produces G)."""
    paia.updated = datetime.now()
    sync_gear(paia)  # Derives all GEAR scores from experience_events
    get_paia_path(storage_dir, paia.name).write_text(paia.model_dump_json(indent=2))


def update_construction_docs(paia: PAIA, comp_type: str, comp_name: str) -> None:
    """Update construction_docs for a component."""
    if not paia.git_dir:
        return
    project_dir = Path(paia.git_dir)
    comp_dir = project_dir / "construction_docs" / "01_components" / comp_type
    comp_dir.mkdir(parents=True, exist_ok=True)

    comp = _find_component(paia, comp_type, comp_name)
    if not comp:
        return

    doc_path = comp_dir / f"{comp_name}.md"
    doc_path.write_text(generate_component_doc(comp, comp_type))
    update_gear_status_doc(paia)


def update_gear_status_doc(paia: PAIA) -> None:
    """Update the GEAR status overview doc."""
    if not paia.git_dir:
        return

    project_dir = Path(paia.git_dir)
    status_path = project_dir / "construction_docs" / "02_gear_status.md"

    lines = ["# [VEHICLE] Hull Status", "",
             f"**Flight Level:** {paia.gear_state.level} | **Phase:** {paia.gear_state.phase.value.upper()}",
             f"**Energy:** {paia.gear_state.total_points} pts", "", "## [VEHICLE] Subsystems by Type", ""]

    for comp_type in COMPONENT_TYPES:
        comps = getattr(paia, comp_type, [])
        if comps:
            lines.append(f"### {comp_type.title()} ({len(comps)})")
            for c in comps:
                tier_badge = f"[{c.tier.value}]" if c.tier.value != "none" else "[--]"
                gold_badge = {"quarantine": "Q", "crystal": "C", "golden": "G"}[c.golden.value]
                lines.append(f"- {tier_badge}[{gold_badge}] **{c.name}** - {c.description[:40]}...")
            lines.append("")

    gs = golden_summary(paia)
    lines.extend(["## [VEHICLE] Construction Summary",
                  f"- **Subsystems:** {gs['golden']}G | {gs['crystal']}C | {gs['quarantine']}Q",
                  f"- **Hull:** {'[CROWNING] CONSTRUCTED' if paia.gear_state.is_constructed else '[TOWERING] IN PROGRESS'}"])

    status_path.write_text("\n".join(lines))
