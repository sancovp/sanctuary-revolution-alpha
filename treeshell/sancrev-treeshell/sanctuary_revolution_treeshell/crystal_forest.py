"""Crystal Forest — HOME screen functions. Ported from SEED MCP.

Data sources: .course_state JSON, skillmanager _equipped.json, sanctum GEAR.
"""

import json
import os
from pathlib import Path

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def _extract_text(result) -> str:
    """Extract text from strata execute_action results (handles TextContent objects)."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = []
        for item in result:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if isinstance(result, dict) and result.get("result"):
        return _extract_text(result["result"])
    if hasattr(result, "text"):
        return result.text
    return str(result)


def _load_course_state() -> dict:
    course_file = Path(HEAVEN_DATA_DIR) / "omnisanc_core" / ".course_state"
    if course_file.exists():
        try:
            return json.loads(course_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


async def cf_last_activity() -> str:
    """Aggregate last_* tracking data for HOME HUD."""
    state = _load_course_state()
    lines = ["# Last Activity\n"]

    lines.append(f"**Last Oriented**: {state.get('last_oriented_path', 'None')}")
    lines.append(f"**Current Course**: {state.get('project_paths', 'None')}")
    lines.append(f"**Domain**: {state.get('domain', 'None')} / {state.get('subdomain', 'None')}")
    lines.append(f"**Flight Active**: {state.get('flight_selected', False)}")
    lines.append(f"**Session Active**: {state.get('session_active', False)}")

    if state.get("was_compacted"):
        lines.append("\nContext was compacted — resume with continue_course() then orient()")

    return "\n".join(lines)


async def cf_orient() -> str:
    """Orientation summary via starlog orient() through strata execute_action."""
    try:
        from strata.treeshell_functions import execute_action
        result = await execute_action("starlog", "orient")
        text = _extract_text(result)
        return f"# Orientation\n\n{text}"
    except ImportError:
        return "# Orientation\n\nstrata not available — cannot call orient()"
    except Exception as e:
        return f"# Orientation\n\nError calling orient: {e}"


async def cf_gear_status() -> str:
    """GEAR status for HOME HUD. Reads sanctum builder."""
    try:
        from sanctuary_revolution_treeshell.treeshell_functions import sanctum_gear_status
        return await sanctum_gear_status()
    except ImportError:
        return "GEAR: sanctum-builder not available"


async def cf_equipped() -> str:
    """Show equipped skills from skillmanager state."""
    equipped_file = Path(HEAVEN_DATA_DIR) / "skills" / "_equipped.json"
    if not equipped_file.exists():
        return "No skills equipped."

    try:
        equipped = json.loads(equipped_file.read_text())
        if not equipped:
            return "No skills equipped."
        lines = ["# Equipped Skills\n"]
        for name in equipped:
            lines.append(f"- {name}")
        return "\n".join(lines)
    except (json.JSONDecodeError, OSError) as e:
        return f"Error reading equipped skills: {e}"


async def cf_home() -> str:
    """Full HOME screen HUD combining all data sources."""
    sections = ["# Crystal Forest — HOME\n"]

    sections.append(await cf_orient())
    sections.append(f"\n{await cf_last_activity()}")

    gear = await cf_gear_status()
    if gear and "not available" not in gear:
        sections.append(f"\n# GEAR Status\n{gear}")

    sections.append(f"\n{await cf_equipped()}")
    sections.append("\n---")
    sections.append("**Navigate**: `jump sancrev` (game) | `jump gnosys` (tools) | `jump skills` (manage)")

    return "\n".join(sections)


def cf_home_sync() -> str:
    """Sync HUD for HPI description resolution (dynamic_call requires sync).

    Reads files directly instead of going through async strata calls.
    Full async cf_home() still available via exec on the node.
    """
    state = _load_course_state()
    sections = ["# Crystal Forest — HOME\n"]
    sections.append("**REQUIRED**: Use the skill `rehydrate-from-memory` to load context before doing anything else.\n")

    # Orientation (sync - read course state directly)
    sections.append("# Orientation\n")
    if state.get("last_oriented"):
        sections.append(f"**Last Oriented**: {state.get('last_oriented')}")
    project = state.get("projects", [])
    if project:
        sections.append(f"**Project**: {project[0] if isinstance(project, list) else project}")
    if state.get("description"):
        sections.append(f"**Description**: {state['description']}")
    if state.get("mission_active"):
        sections.append(f"**Mission**: {state.get('mission_id', 'unknown')} (step {state.get('mission_step', 0)})")
    if state.get("was_compacted"):
        sections.append("\nContext was compacted — resume with continue_course() then orient()")

    # Last activity
    sections.append(f"\n# Last Activity\n")
    sections.append(f"**Domain**: {state.get('domain', 'None')} / {state.get('subdomain', 'None')}")
    sections.append(f"**Flight Active**: {state.get('flight_selected', False)}")
    sections.append(f"**Session Active**: {state.get('session_active', False)}")

    # Equipped skills (sync - read JSON file)
    equipped_file = Path(HEAVEN_DATA_DIR) / "skills" / "_equipped.json"
    if equipped_file.exists():
        try:
            equipped = json.loads(equipped_file.read_text())
            if equipped:
                sections.append("\n# Equipped Skills\n")
                for name in equipped:
                    sections.append(f"- {name}")
            else:
                sections.append("\nNo skills equipped.")
        except (json.JSONDecodeError, OSError):
            sections.append("\nNo skills equipped.")
    else:
        sections.append("\nNo skills equipped.")

    sections.append("\n---")
    sections.append("**Navigate**: `jump sancrev` (game) | `jump gnosys` (tools) | `jump skills` (manage)")

    return "\n".join(sections)
