"""CreatePRDTool — Heaven tool that the Prompt Engineer calls to fill out a typed PRD.

The PE agent calls this tool with every slot typed.
The tool validates via PRD.from_dict() and saves to the queue.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def create_prd(
    name: str,
    description: str,
    architecture: str,
    links: str,
    behavioral_assertions: str,
    types: str = "[]",
    imports_available: str = "[]",
    system_prompt_identity: str = "",
    file_structure: str = "{}",
    project_id: str = "",
    queue_dir: str = "",
) -> str:
    """Create a typed Product Requirements Document (PRD) and save it to the build queue.

    Every field must be filled out. behavioral_assertions are CRITICAL —
    they define what execute() must produce. The PRD is validated and saved
    to the queue directory for the Planner → Bandit → OctoCoder pipeline.

    Args:
        name: Project name (snake_case, e.g. 'rest_api_widgets')
        description: What this project does
        architecture: 'Chain' or 'EvalChain'
        links: JSON array of link specs: [{"name": "...", "kind": "SDNAC", "description": "...", "inputs": [...], "outputs": [...]}]
        behavioral_assertions: JSON array of behavioral assertions: [{"description": "...", "setup": "...", "call": "...", "assertions": ["..."]}]. CRITICAL — defines correctness.
        types: JSON array of type specs: [{"name": "...", "kind": "dataclass", "fields": {...}, "description": "..."}]
        imports_available: JSON array of import strings
        system_prompt_identity: Who this agent is
        file_structure: JSON object mapping path to description: {"path/file.py": "what it does"}
        project_id: GIINT project ID. If set, links this PRD to an existing project so the Planner extends it instead of creating a new one.
        queue_dir: Queue directory path (default: /tmp/compoctopus_queue)

    Returns:
        Success message with PRD details, or ERROR message
    """
    from compoctopus.prd import PRD

    print(f"🔧 CreatePRD({name})")

    # Parse JSON string fields
    try:
        prd_dict = {
            "name": name,
            "description": description,
            "architecture": architecture,
            "links": json.loads(links),
            "types": json.loads(types),
            "behavioral_assertions": json.loads(behavioral_assertions),
            "imports_available": json.loads(imports_available),
            "system_prompt_identity": system_prompt_identity,
            "file_structure": json.loads(file_structure),
        }
        if project_id:
            prd_dict["project_id"] = project_id
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON in one of the fields: {e}"

    # Validate via PRD.from_dict
    try:
        prd = PRD.from_dict(prd_dict)
    except (ValueError, KeyError, TypeError) as e:
        return f"ERROR: PRD validation failed: {e}"

    # Warn if no behavioral assertions
    if not prd.behavioral_assertions:
        return (
            "ERROR: behavioral_assertions is empty. "
            "You MUST include at least 1 behavioral assertion. "
            "Each one needs: description, setup, call, assertions."
        )

    # Save to queue
    path = prd.save_to_queue(queue_dir=queue_dir or None)

    return (
        f"✅ PRD '{prd.name}' saved to: {path}\n"
        f"   Links: {len(prd.links)}\n"
        f"   Types: {len(prd.types)}\n"
        f"   Behavioral assertions: {len(prd.behavioral_assertions)}\n"
        f"   Files: {len(prd.file_structure)}\n"
        f"   Ready for Planner → Bandit → OctoCoder pipeline."
    )


# Create the Heaven tool from the function
try:
    from heaven_base.make_heaven_tool_from_docstring import make_heaven_tool_from_docstring
    CreatePRDTool = make_heaven_tool_from_docstring(create_prd, tool_name="CreatePRD")
except ImportError:
    CreatePRDTool = None
    logger.warning("heaven_base not available — CreatePRDTool disabled")
