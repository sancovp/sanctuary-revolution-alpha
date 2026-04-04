#!/usr/bin/env python3
"""
CANOPY Schedule - Master schedule orchestration for AI+Human collaboration

Manages the master schedule of work items with three collaboration types:
- AI+Human: Work together on missions
- AI-Only: AI can complete autonomously
- Human-Only: Waiting for human completion

v0: Adds execution tracking for OPERA pattern discovery
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Import HEAVEN registry
try:
    from heaven_base.tools.registry_tool import registry_util_func
except ImportError:
    logger.warning("heaven_base not available - schedule will not persist", exc_info=True)
    def registry_util_func(*args, **kwargs):
        return "Registry not available"

# Registry names
SCHEDULE_REGISTRY = "canopy_master_schedule"
OPERADIC_LEDGER_REGISTRY = "operadic_ledger"


def _record_execution(item: Dict[str, Any]) -> None:
    """
    Auto-record completed schedule item to operadic_ledger by date.

    Storage structure: operadic_ledger/YYYY-MM-DD/item_id
    """
    try:
        # Get today's date for ledger organization
        today = datetime.now().strftime('%Y-%m-%d')

        # Write to ledger under today's date
        registry_util_func(
            "add",
            registry_name=f"{OPERADIC_LEDGER_REGISTRY}/{today}",
            key=item["item_id"],
            value_dict=item
        )

        logger.info(f"Recorded execution to operadic_ledger/{today}/{item['item_id']}")

    except Exception as e:
        logger.error(f"Failed to record execution to operadic_ledger: {e}", exc_info=True)
        # Don't fail the completion if recording fails


def add_to_schedule(
    item_type: str,
    description: str,
    execution_type: str,
    execution_type_decision_explanation: str,
    priority: int = 5,
    mission_type: Optional[str] = None,
    mission_type_domain: Optional[str] = None,
    human_capability: Optional[str] = None,
    source_type: str = "freestyle",
    source_operadic_flow_id: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add work item to master schedule

    Args:
        item_type: "AI+Human", "AI-Only", or "Human-Only"
        description: Human-readable description of the work
        execution_type: "mission" or "plotted_course" - how this work will be executed
        execution_type_decision_explanation: Why this execution type was chosen
        priority: 1-10 priority (10 = highest, default 5)
        mission_type: Optional mission type template ID (for AI work)
        mission_type_domain: Optional domain containing mission type
        human_capability: Optional human capability (for Human-Only or AI+Human tasks)
        source_type: "freestyle" or "opera" (default: freestyle)
        source_operadic_flow_id: Optional OperadicFlow ID if opera-sourced
        variables: Optional variables for mission template
        metadata: Optional additional metadata

    Returns:
        Result with item_id
    """
    try:
        # Validate item_type
        valid_types = ["AI+Human", "AI-Only", "Human-Only"]
        if item_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid item_type. Must be one of: {valid_types}"
            }

        # Validate execution_type
        valid_execution_types = ["mission", "plotted_course"]
        if execution_type not in valid_execution_types:
            return {
                "success": False,
                "error": f"Invalid execution_type. Must be one of: {valid_execution_types}"
            }

        # Validate priority
        if not (1 <= priority <= 10):
            return {
                "success": False,
                "error": "Priority must be between 1-10"
            }

        # Validate source_type
        valid_source_types = ["freestyle", "opera"]
        if source_type not in valid_source_types:
            return {
                "success": False,
                "error": f"Invalid source_type. Must be one of: {valid_source_types}"
            }

        # Get current schedule
        schedule = _get_schedule_items()

        # Generate item_id
        item_id = f"canopy_{len(schedule) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create schedule item
        item = {
            "item_id": item_id,
            "type": item_type,
            "description": description,
            "execution_type": execution_type,
            "execution_type_decision_explanation": execution_type_decision_explanation,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "mission_type": mission_type,
            "mission_type_domain": mission_type_domain,
            "human_capability": human_capability,
            "source_type": source_type,
            "source_operadic_flow_id": source_operadic_flow_id,
            "variables": variables or {},
            "metadata": metadata or {}
        }

        # Add to schedule
        schedule[item_id] = item

        # Save to registry
        registry_util_func(
            "add",
            registry_name=SCHEDULE_REGISTRY,
            key=item_id,
            value_dict=item
        )

        # Mirror to CartON
        _mirror_to_carton(item, event="created")

        return {
            "success": True,
            "item_id": item_id,
            "message": f"Added {item_type} item to schedule",
            "priority": priority
        }

    except Exception as e:
        logger.error(f"Error adding to schedule: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _mirror_to_carton(item: Dict[str, Any], event: str = "created") -> None:
    """Mirror a Canopy schedule item to CartON via carton_queue.

    Writes a concept to carton_queue/ for the observation worker daemon
    to process into Neo4j. This makes Canopy items queryable in the
    knowledge graph alongside GIINT hierarchy concepts.

    Args:
        item: The schedule item dict
        event: "created" or "completed"
    """
    try:
        import json
        import uuid
        from pathlib import Path

        heaven_data = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data") if 'os' in dir() else "/tmp/heaven_data"
        try:
            import os as _os
            heaven_data = _os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        except Exception:
            pass

        queue_dir = Path(heaven_data) / "carton_queue"
        queue_dir.mkdir(parents=True, exist_ok=True)

        item_id = item.get("item_id", "unknown")
        concept_name = f"Canopy_Item_{item_id}"
        status = item.get("status", "pending")
        item_type = item.get("type", "AI-Only")
        description = item.get("description", "")
        project_name = item.get("variables", {}).get("project_name", "")

        if event == "completed":
            desc = f"[COMPLETED] {item_type}: {description}"
        else:
            desc = f"[{status.upper()}] {item_type}: {description}"

        # Build relationships
        rels = [
            {"relationship": "is_a", "related": ["Canopy_Schedule_Item"]},
            {"relationship": "instantiates", "related": ["Canopy_Item_Template"]},
        ]

        if project_name:
            rels.append({"relationship": "part_of", "related": [f"Giint_Project_{project_name}"]})
        else:
            rels.append({"relationship": "part_of", "related": ["Canopy_Master_Schedule"]})

        if item.get("source_operadic_flow_id"):
            rels.append({"relationship": "has_source_flow", "related": [item["source_operadic_flow_id"]]})

        queue_data = {
            "raw_concept": True,
            "concept_name": concept_name,
            "description": desc,
            "relationships": rels,
            "desc_update_mode": "replace",
            "hide_youknow": False,
            "is_soup": False,
            "soup_reason": None,
            "source": "canopy_schedule_mirror",
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        queue_file = queue_dir / f"{timestamp}_{unique_id}_canopy.json"

        with open(queue_file, "w") as f:
            json.dump(queue_data, f, indent=2)

        logger.info(f"Mirrored Canopy item {item_id} to CartON ({event})")

    except Exception as e:
        logger.warning(f"Failed to mirror Canopy item to CartON: {e}")


def _set_active_hc_from_item(item: Dict[str, Any]) -> None:
    """Set active hypercluster from a schedule item's project context.

    Checks variables.project_name and metadata.giint_project for the
    starsystem/project name, then writes the corresponding Hypercluster_
    name to /tmp/active_hypercluster.txt so memory compilation shows
    the right context.
    """
    try:
        from pathlib import Path

        project_name = None
        # Check variables first (mission template substitution)
        variables = item.get("variables", {})
        if variables.get("project_name"):
            project_name = variables["project_name"]
        # Check metadata
        elif item.get("metadata", {}).get("giint_project"):
            project_name = item["metadata"]["giint_project"]

        if project_name:
            # Normalize: strip Giint_Project_ prefix if present
            hc_name = project_name.replace("Giint_Project_", "").replace("GIINT_Project_", "")
            hc_concept = f"Hypercluster_{hc_name}"
            Path("/tmp/active_hypercluster.txt").write_text(hc_concept)
            logger.info(f"Active HC set to {hc_concept} from schedule item {item.get('item_id')}")
    except Exception as e:
        logger.warning(f"Failed to set active HC from item: {e}")


def get_next_item(item_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get next pending item from schedule

    Args:
        item_type: Optional filter by type ("AI+Human", "AI-Only", "Human-Only")

    Returns:
        Next item to work on, or None if schedule empty
    """
    try:
        schedule = _get_schedule_items()

        if not schedule:
            return {
                "success": True,
                "next_item": None,
                "message": "Schedule is empty"
            }

        # Filter pending items
        pending_items = [
            item for item in schedule.values()
            if item["status"] == "pending"
        ]

        # Filter by type if specified
        if item_type:
            pending_items = [
                item for item in pending_items
                if item["type"] == item_type
            ]

        if not pending_items:
            return {
                "success": True,
                "next_item": None,
                "message": f"No pending {item_type} items" if item_type else "No pending items"
            }

        # Sort by priority (highest first)
        pending_items.sort(key=lambda x: x["priority"], reverse=True)

        next_item = pending_items[0]

        # AUTO-SET ACTIVE HYPERCLUSTER from item's project context
        # This wires get_next → memory compilation: pulling a task
        # automatically sets the active HC so MEMORY.md shows the right context
        _set_active_hc_from_item(next_item)

        return {
            "success": True,
            "next_item": next_item,
            "pending_count": len(pending_items)
        }

    except Exception as e:
        logger.error(f"Error getting next item: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def view_schedule(status_filter: Optional[str] = None) -> str:
    """
    View master schedule with optional status filter

    Args:
        status_filter: Optional "pending", "in_progress", "completed"

    Returns:
        Formatted schedule display
    """
    try:
        schedule = _get_schedule_items()

        if not schedule:
            return "📋 Master Schedule is empty\n\nAdd items with: canopy.add_to_schedule()"

        # Filter by status
        items = list(schedule.values())
        if status_filter:
            items = [item for item in items if item["status"] == status_filter]

        # Sort by priority
        items.sort(key=lambda x: (x["status"] != "pending", -x["priority"], x["created_at"]))

        # Format output
        output = [f"📋 CANOPY Master Schedule ({len(items)} items)"]

        if status_filter:
            output.append(f"Filter: {status_filter}")

        output.append("")

        for item in items:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅"
            }.get(item["status"], "❓")

            type_emoji = {
                "AI+Human": "👥",
                "AI-Only": "🤖",
                "Human-Only": "👤"
            }.get(item["type"], "❓")

            source_emoji = "✍️" if item.get("source_type") == "freestyle" else "🎭"

            output.append(f"{status_emoji} {type_emoji} {source_emoji} [{item['priority']}] {item['item_id']}")
            output.append(f"   Type: {item['type']}")
            output.append(f"   Description: {item['description']}")
            output.append(f"   Execution Type: {item.get('execution_type', 'N/A')}")
            output.append(f"   Execution Reasoning: {item.get('execution_type_decision_explanation', 'N/A')}")
            output.append(f"   Source: {item.get('source_type', 'freestyle')}")

            if item.get("mission_type"):
                output.append(f"   Mission Type: {item['mission_type']} ({item['mission_type_domain']})")

            if item.get("human_capability"):
                output.append(f"   Human Capability: {item['human_capability']}")

            if item.get("source_operadic_flow_id"):
                output.append(f"   Source OperadicFlow: {item['source_operadic_flow_id']}")

            output.append(f"   Status: {item['status']}")
            output.append("")

        return '\n'.join(output)

    except Exception as e:
        logger.error(f"Error viewing schedule: {e}", exc_info=True)
        return f"❌ Error viewing schedule: {str(e)}"


def mark_complete(item_id: str) -> Dict[str, Any]:
    """
    Mark schedule item as completed

    Args:
        item_id: Item to mark complete

    Returns:
        Update result
    """
    try:
        schedule = _get_schedule_items()

        if item_id not in schedule:
            return {
                "success": False,
                "error": f"Item '{item_id}' not found in schedule"
            }

        item = schedule[item_id]
        item["status"] = "completed"
        item["completed_at"] = datetime.now().isoformat()

        # Update in registry
        registry_util_func(
            "update",
            registry_name=SCHEDULE_REGISTRY,
            key=item_id,
            value_dict=item
        )

        # Auto-record to operadic_ledger
        _record_execution(item)

        # Mirror completion to CartON
        _mirror_to_carton(item, event="completed")

        return {
            "success": True,
            "item_id": item_id,
            "message": f"Marked {item['type']} item as completed"
        }

    except Exception as e:
        logger.error(f"Error marking complete: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def update_item_status(item_id: str, status: str) -> Dict[str, Any]:
    """
    Update item status

    Args:
        item_id: Item to update
        status: New status ("pending", "in_progress", "completed")

    Returns:
        Update result
    """
    try:
        valid_statuses = ["pending", "in_progress", "completed"]
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {valid_statuses}"
            }

        schedule = _get_schedule_items()

        if item_id not in schedule:
            return {
                "success": False,
                "error": f"Item '{item_id}' not found in schedule"
            }

        item = schedule[item_id]
        item["status"] = status

        if status == "completed":
            item["completed_at"] = datetime.now().isoformat()

        # Update in registry
        registry_util_func(
            "update",
            registry_name=SCHEDULE_REGISTRY,
            key=item_id,
            value_dict=item
        )

        # Auto-record to operadic_ledger if completed
        if status == "completed":
            _record_execution(item)

        return {
            "success": True,
            "item_id": item_id,
            "message": f"Updated status to {status}"
        }

    except Exception as e:
        logger.error(f"Error updating status: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _get_schedule_items() -> Dict[str, Any]:
    """
    Get all schedule items from registry

    Returns:
        Dictionary of item_id -> item_data
    """
    try:
        result = registry_util_func("get_all", registry_name=SCHEDULE_REGISTRY)

        # Parse registry result
        if "Items in registry" in result:
            try:
                import ast
                start_idx = result.find("{")
                if start_idx != -1:
                    return ast.literal_eval(result[start_idx:])
            except Exception:
                logger.warning(f"Failed to parse schedule registry result", exc_info=True)

        return {}

    except Exception as e:
        logger.error(f"Failed to get schedule items: {e}", exc_info=True)
        return {}
