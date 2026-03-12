"""
TreeShell Node Learnings - JIT injection of learnings via CartON.

This module provides:
1. Bidirectional converter between TreeShell semantic addresses and CartON concept names
2. get_node_learnings() - called via dynamic_call to inject learnings at render time
3. add_node_learning() - TreeShell action to add learnings (bijective with direct CartON)
"""

import json


def semantic_to_carton(semantic_addr: str, app_id: str = None) -> str:
    """Convert TreeShell semantic address to CartON concept name.

    Args:
        semantic_addr: TreeShell semantic address (e.g., "skill_manager.equip")
        app_id: TreeShell app_id (e.g., "skillmanager_treeshell")

    Examples (with app_id="skillmanager_treeshell"):
        skill_manager.equip → Skillmanager_Treeshell_Node_Skill_Manager_Equip_Learnings

    Examples (without app_id - legacy fallback):
        agent_management.equipment.tools → TreeShell_Node_Agent_Management_Equipment_Tools_Learnings
    """
    # Convert dots to underscores, title case each segment
    parts = semantic_addr.split(".")
    normalized = "_".join(p.replace("_", " ").title().replace(" ", "_") for p in parts)

    if app_id:
        # Use app_id as prefix: skillmanager_treeshell → Skillmanager_Treeshell
        app_prefix = "_".join(p.replace("_", " ").title().replace(" ", "_") for p in app_id.split("_"))
        return f"{app_prefix}_Node_{normalized}_Learnings"
    else:
        # Legacy fallback
        return f"TreeShell_Node_{normalized}_Learnings"


def carton_to_semantic(concept_name: str) -> str:
    """Convert CartON concept name back to TreeShell semantic address.

    Examples:
        TreeShell_Node_Agent_Management_Equipment_Tools_Learnings → agent_management.equipment.tools
        TreeShell_Node_Save_Variable_Learnings → save_variable

    Note: This is a heuristic conversion - underscores in original names become ambiguous.
    """
    if concept_name.startswith("TreeShell_Node_") and concept_name.endswith("_Learnings"):
        inner = concept_name[15:-10]  # Remove "TreeShell_Node_" and "_Learnings"
        # Convert underscores back to dots and lowercase
        # This is lossy - can't distinguish word boundaries from path separators
        parts = inner.split("_")
        return ".".join(p.lower() for p in parts)
    return concept_name


def get_node_definition(semantic_addr: str, app_id: str = None) -> dict | None:
    """Read full node definition from CartON (source-of-truth flip).

    Returns the raw node dict (type, options, signature, args_schema, domain)
    if stored by node_sync, or None if not available.
    """
    from .node_sync import _node_concept_name
    concept_name = _node_concept_name(semantic_addr, app_id)
    try:
        from carton_mcp import get_concept
        result = get_concept(concept_name)
        if result and result.get("description"):
            desc = result["description"]
            marker = "<!-- NODE_DEF:"
            if marker in desc:
                start = desc.index(marker) + len(marker)
                end = desc.index(" -->", start)
                return json.loads(desc[start:end])
    except (ImportError, Exception):
        pass
    return None


def get_node_learnings(semantic_addr: str, app_id: str = None) -> str:
    """Query CartON for node learnings. Called via dynamic_call.

    Args:
        semantic_addr: TreeShell semantic address (e.g., "skill_manager.equip")
        app_id: TreeShell app_id (e.g., "skillmanager_treeshell")

    Returns:
        Formatted learnings string, or empty string if no learnings exist.
    """
    concept_name = semantic_to_carton(semantic_addr, app_id)
    try:
        # Import CartON MCP client
        from carton_mcp import get_concept
        result = get_concept(concept_name)
        if result and result.get("description"):
            return f"\n\n**Learnings:**\n{result['description']}"
    except ImportError:
        # CartON not available - try direct file access as fallback
        try:
            import os
            from pathlib import Path
            carton_dir = Path(os.environ.get("CARTON_DIR", "/tmp/heaven_data/carton"))
            concept_file = carton_dir / f"{concept_name}.md"
            if concept_file.exists():
                content = concept_file.read_text().strip()
                if content:
                    return f"\n\n**Learnings:**\n{content}"
        except Exception:
            pass
    except Exception:
        pass
    return ""


async def add_node_learning(semantic_addr: str, content: str, app_id: str = None) -> str:
    """Add learning to a TreeShell node via CartON.

    Bijective with direct CartON add_concept() using naming convention.

    Args:
        semantic_addr: TreeShell semantic address (e.g., "skill_manager.equip")
        content: The learning content to add
        app_id: TreeShell app_id (e.g., "skillmanager_treeshell")

    Returns:
        Confirmation message
    """
    concept_name = semantic_to_carton(semantic_addr, app_id)

    # Build IS_A and PART_OF based on app_id
    if app_id:
        app_prefix = "_".join(p.replace("_", " ").title().replace(" ", "_") for p in app_id.split("_"))
        is_a_target = f"{app_prefix}_Node_Learning"
        part_of_target = f"{app_prefix}_Learnings_Collection"
    else:
        is_a_target = "TreeShell_Node_Learning"
        part_of_target = "TreeShell_Learnings_Collection"

    try:
        # Use CartON add_concept with append mode
        from carton_mcp import add_concept_tool_func as add_concept
        add_concept(
            concept_name=concept_name,
            description=content,
            relationships=[
                {"relationship": "is_a", "related": [is_a_target]},
                {"relationship": "part_of", "related": [part_of_target]}
            ],
            desc_update_mode="append"  # Accumulate learnings
        )
        return f"[LEARNING] Added to node {semantic_addr} (CartON: {concept_name})"
    except ImportError:
        return f"[ERROR] CartON not available. Install carton_mcp package."
    except Exception as e:
        return f"[ERROR] Failed to add learning: {e}"
