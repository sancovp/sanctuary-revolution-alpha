"""
TreeShell Node Sync - Background sync of rendered nodes to CartON.

Only syncs MENU and NAVIGATION responses (actual node definitions).
Skips execution results, errors, chains — those are outputs, not nodes.
Uses semantic node name for identity (never numeric coordinates).
Hash comparison to detect description changes.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

# In-memory cache: concept_name -> description_hash
_synced_nodes: dict = {}

# Response actions that represent actual node definitions
_NODE_ACTIONS = {"menu", "navigation_overview", "navigate", "jump"}


def _get_queue_dir() -> Path:
    """Get CartON queue directory."""
    heaven_data = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
    queue_dir = Path(heaven_data) / "carton_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    return queue_dir


def _node_concept_name(semantic_name: str, app_id: str = None) -> str:
    """Convert TreeShell semantic node name to CartON concept name.

    Identity comes from the full semantic address (e.g. 'skills.equip'),
    NEVER from numeric coordinates (which are ephemeral).

    Examples:
        ("skills.equip", "sancrev_treeshell") -> "Sancrev_Treeshell_Node_Skills_Equip"
        ("skills.equip", None) -> "TreeShell_Node_Skills_Equip"
    """
    parts = semantic_name.split(".")
    normalized = "_".join(
        p.replace("_", " ").title().replace(" ", "_") for p in parts
    )

    if app_id and app_id != "default":
        app_prefix = "_".join(
            p.replace("_", " ").title().replace(" ", "_")
            for p in app_id.split("_")
        )
        return f"{app_prefix}_Node_{normalized}"
    return f"TreeShell_Node_{normalized}"


def sync_node_to_carton(response: dict) -> None:
    """Fire-and-forget sync of a rendered node to CartON queue.

    Only syncs menu/navigation responses (actual node definitions).
    Skips execution results, errors, chains.
    Uses full semantic address for identity, never numeric coordinates.

    Args:
        response: Full TreeShell response dict from handle_command()
    """
    # Only sync node definitions, not execution results
    action = response.get("action", "")
    has_menu = "menu_options" in response
    if action not in _NODE_ACTIONS and not has_menu:
        return

    # Get full semantic address — this is the REAL identity
    semantic_name = response.get("semantic_address", "").strip()

    # No semantic address = no sync. Never use numeric position as identity.
    if not semantic_name:
        return
    app_id = response.get("app_id", "default")
    version = response.get("version", "unknown")
    concept_name = _node_concept_name(semantic_name, app_id)

    # Build concept description
    domain = response.get("domain", "general")
    description = response.get("description", "")
    signature = response.get("signature", "")
    coordinate = response.get("_source", f"coordinate:{response.get('position', '?')}")

    if isinstance(description, str) and len(description) > 500:
        description = description[:500] + "..."

    concept_desc = f"TreeShell node '{semantic_name}' at {coordinate}. {description}"
    if signature:
        concept_desc += f" Args: {signature}"

    # Store raw node definition for CartON-as-source-of-truth reads
    raw_type = response.get("node_type", "Menu")
    node_def = {
        "type": raw_type.value if hasattr(raw_type, 'value') else str(raw_type),
        "options": response.get("menu_options", {}),
        "signature": signature,
        "args_schema": response.get("args_schema", {}),
        "domain": domain,
    }
    concept_desc += f"\n\n<!-- NODE_DEF:{json.dumps(node_def)} -->"

    # Hash check — skip if description unchanged
    desc_hash = hashlib.md5(concept_desc.encode()).hexdigest()
    cached_hash = _synced_nodes.get(concept_name)
    if cached_hash == desc_hash:
        return
    is_update = cached_hash is not None
    _synced_nodes[concept_name] = desc_hash

    # Build relationships
    if app_id and app_id != "default":
        app_prefix = "_".join(
            p.replace("_", " ").title().replace(" ", "_")
            for p in app_id.split("_")
        )
        collection_name = f"{app_prefix}_Nodes_Collection"
    else:
        collection_name = "TreeShell_Nodes_Collection"

    relationships = [
        {"relationship": "is_a", "related": ["TreeShell_Node"]},
        {"relationship": "part_of", "related": [collection_name]},
        {"relationship": "has_version", "related": [f"TreeShell_Version_{version}"]},
    ]

    if domain and domain != "general" and "NO DOMAIN" not in domain.upper():
        # Sanitize: replace dots with underscores, title case
        safe_domain = domain.replace(".", "_").replace(" ", "_")
        domain_concept = "_".join(p.title() for p in safe_domain.split("_") if p) + "_Domain"
        relationships.append({"relationship": "has_domain", "related": [domain_concept]})

    # Queue file for bg worker (fire-and-forget)
    try:
        queue_dir = _get_queue_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_id = uuid.uuid4().hex[:8]
        queue_file = queue_dir / f"{timestamp}_{unique_id}_concept.json"

        queue_data = {
            "raw_concept": True,
            "concept_name": concept_name,
            "description": concept_desc,
            "relationships": relationships,
            "desc_update_mode": "replace" if is_update else "append",
            "hide_youknow": True,
            "metadata": {
                "source": "treeshell_node_sync",
                "semantic_name": semantic_name,
                "coordinate": coordinate,
                "app_id": app_id,
                "version": version,
                "domain": domain,
                "is_update": is_update,
                "desc_hash": desc_hash,
            },
        }

        queue_file.write_text(json.dumps(queue_data, indent=2))
    except Exception as e:
        import logging
        logging.getLogger("treeshell.node_sync").warning(f"CartON node sync failed for {concept_name}: {e}")
