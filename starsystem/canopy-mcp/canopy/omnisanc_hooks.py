#!/usr/bin/env python3
"""
OMNISANC Hooks for Canopy-OPERA Integration

Three hooks that enforce the architectural boundaries between Canopy and OPERA:
1. Pre-tool Lock: Prevents freestyle Canopy additions when OPERA queue has work
2. Feeding Hook: Expands OPERA items into Canopy when Canopy is empty
3. Pattern Detection Trigger: Runs pattern detection after Canopy item completion
"""

import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Import OPERA pattern detection
try:
    from opera.pattern_detection import detect_patterns
except ImportError:
    logger.warning("opera.pattern_detection not available", exc_info=True)
    def detect_patterns(**kwargs):
        return {"success": False, "error": "OPERA pattern detection not available"}

# Import HEAVEN registry
# PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
try:
    from heaven_base.tools.registry_tool import registry_util_func
except ImportError:
    logger.warning("heaven_base not available - hooks will not function", exc_info=True)
    def registry_util_func(*args, **kwargs):
        return "Registry not available"


OPERA_SCHEDULE_REGISTRY = "opera_schedule"
CANOPY_SCHEDULE_REGISTRY = "canopy_master_schedule"


# ============================================================================
# HOOK 1: PRE-TOOL LOCK
# ============================================================================

def check_opera_lock(source_type: str) -> Optional[str]:
    """
    Pre-tool hook: Check if OPERA schedule is blocking freestyle Canopy additions.

    When OPERA schedule has queued items, freestyle Canopy additions are locked.
    Only opera-sourced items can be added to Canopy.

    Args:
        source_type: "freestyle" or "opera" - determines if lock applies

    Returns:
        Error message if blocked, None if allowed
    """
    try:
        # Opera-sourced items always bypass lock
        if source_type == "opera":
            return None

        # Check if OPERA schedule has items
        result = registry_util_func("get_all", registry_name=OPERA_SCHEDULE_REGISTRY)

        # Parse registry result
        if "Items in registry" in result:
            try:
                start_idx = result.find("{")
                if start_idx != -1:
                    dict_str = result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    opera_items = json.loads(dict_str.replace("'", '"'))

                    # Filter to queued items only
                    queued_items = [
                        item for item in opera_items.values()
                        if isinstance(item, dict) and item.get("status") == "queued"
                    ]

                    if queued_items:
                        # OPERA schedule is not empty - block freestyle
                        return (
                            "❌ CANOPY FREESTYLE SCHEDULE IS LOCKED\n\n"
                            f"OPERA schedule has {len(queued_items)} queued item(s). "
                            "Canopy freestyle is locked when OPERA has work.\n\n"
                            "To add work:\n"
                            "1. Use OPERA tools: opera.add_to_opera_schedule()\n"
                            "2. Or wait for OPERA queue to empty\n"
                            "3. Or complete current OPERA items\n\n"
                            "View OPERA schedule: opera.view_opera_schedule()"
                        )
            except Exception:
                logger.debug("Error parsing OPERA schedule", exc_info=True)

        # OPERA schedule empty or error - allow freestyle
        return None

    except Exception as e:
        logger.error(f"Error checking OPERA lock: {e}", exc_info=True)
        # On error, allow (fail open rather than fail closed)
        return None


# ============================================================================
# HOOK 2: FEEDING HOOK
# ============================================================================

def feed_from_opera_if_needed() -> Dict[str, Any]:
    """
    Feeding hook: When Canopy schedule is empty, pull from OPERA and expand.

    This is called by OMNISANC automation (not directly exposed as MCP tool).

    Flow:
    1. Check if Canopy schedule is empty or low (<3 items)
    2. Get top N items from OPERA schedule (priority order)
    3. For each OPERA item:
       a. Call expand_operadic_flow_to_canopy_items()
       b. Add expanded items to Canopy with source_type='opera'
       c. Remove from OPERA schedule
    4. Return feeding report

    Returns:
        Feeding report with items added
    """
    try:
        # Import Canopy schedule functions
        from canopy.schedule import add_to_schedule, _get_schedule_items

        # Check Canopy schedule status
        schedule = _get_schedule_items()
        pending_items = [
            item for item in schedule.values()
            if item.get("status") == "pending"
        ]

        # Only feed if Canopy has <3 pending items
        if len(pending_items) >= 3:
            return {
                "success": True,
                "message": f"Canopy has {len(pending_items)} pending items - no feeding needed",
                "fed_count": 0
            }

        # Get top items from OPERA schedule
        feed_count = 3 - len(pending_items)
        opera_items = _get_top_opera_items(feed_count)

        if not opera_items:
            return {
                "success": True,
                "message": "OPERA schedule is empty - nothing to feed",
                "fed_count": 0
            }

        # Expand and feed each OPERA item
        fed_items = []
        errors = []

        for opera_item in opera_items:
            try:
                # Expand OperadicFlow to Canopy items
                operadic_flow_id = opera_item.get("operadic_flow_id")
                schedule_entry_id = opera_item.get("schedule_entry_id")

                expanded_result = _expand_operadic_flow_to_canopy_items(operadic_flow_id)

                if not expanded_result.get("success"):
                    errors.append(f"Failed to expand {operadic_flow_id}: {expanded_result.get('error')}")
                    continue

                # Add each Canopy item to schedule
                canopy_items = expanded_result.get("canopy_items", [])

                for canopy_item in canopy_items:
                    # Add to Canopy schedule
                    add_result = add_to_schedule(**canopy_item)

                    if add_result.get("success"):
                        fed_items.append(add_result.get("item_id"))
                    else:
                        errors.append(f"Failed to add item: {add_result.get('error')}")

                # Remove from OPERA schedule
                _remove_from_opera_schedule(schedule_entry_id)

            except Exception as e:
                logger.error(f"Error feeding OPERA item: {e}", exc_info=True)
                errors.append(f"Exception feeding item: {str(e)}")

        return {
            "success": True,
            "message": f"Fed {len(fed_items)} items from OPERA to Canopy",
            "fed_count": len(fed_items),
            "fed_items": fed_items,
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Error in OPERA feeding hook: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _get_top_opera_items(count: int) -> List[Dict[str, Any]]:
    """
    Get top N items from OPERA schedule by priority.

    Args:
        count: Number of items to retrieve

    Returns:
        List of OPERA schedule items
    """
    try:
        result = registry_util_func("get_all", registry_name=OPERA_SCHEDULE_REGISTRY)

        # Parse registry result
        if "Items in registry" in result:
            try:
                start_idx = result.find("{")
                if start_idx != -1:
                    dict_str = result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    opera_items = json.loads(dict_str.replace("'", '"'))

                    # Filter to queued items
                    queued_items = [
                        item for item in opera_items.values()
                        if isinstance(item, dict) and item.get("status") == "queued"
                    ]

                    # Sort by priority (highest first), then by queued_at
                    queued_items.sort(key=lambda x: (-x.get("priority", 5), x.get("queued_at", "")))

                    # Return top N
                    return queued_items[:count]
            except Exception:
                logger.warning("Failed to parse OPERA schedule", exc_info=True)

        return []

    except Exception as e:
        logger.error(f"Error getting top OPERA items: {e}", exc_info=True)
        return []


def _expand_operadic_flow_to_canopy_items(operadic_flow_id: str) -> Dict[str, Any]:
    """
    Expand OperadicFlow into Canopy items.

    Args:
        operadic_flow_id: OperadicFlow to expand

    Returns:
        Result with canopy_items list
    """
    try:
        # Get OperadicFlow from golden library
        result = registry_util_func(
            "get",
            registry_name="opera_operadic_flows",
            key=operadic_flow_id
        )

        # Parse result
        if "Value for key" in result:
            start_idx = result.find("{")
            if start_idx != -1:
                dict_str = result[start_idx:]
                dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                operadic_flow = json.loads(dict_str.replace("'", '"'))

                # Extract sequence
                sequence = operadic_flow.get("sequence", [])

                if not sequence:
                    return {
                        "success": False,
                        "error": f"OperadicFlow '{operadic_flow_id}' has no sequence"
                    }

                # Generate Canopy items from sequence
                canopy_items = []
                for idx, step in enumerate(sequence):
                    canopy_item = {
                        "item_type": step.get("item_type"),
                        "description": step.get("description", f"Step {idx + 1} of {operadic_flow_id}"),
                        "execution_type": step.get("execution_type"),
                        "execution_type_decision_explanation": f"From OperadicFlow: {operadic_flow_id}",
                        "priority": step.get("priority", 5),
                        "mission_type": step.get("mission_type"),
                        "mission_type_domain": step.get("mission_type_domain"),
                        "human_capability": step.get("human_capability"),
                        "source_type": "opera",
                        "source_operadic_flow_id": operadic_flow_id,
                        "variables": step.get("variables", {}),
                        "metadata": step.get("metadata", {})
                    }
                    canopy_items.append(canopy_item)

                return {
                    "success": True,
                    "operadic_flow_id": operadic_flow_id,
                    "canopy_items": canopy_items,
                    "count": len(canopy_items)
                }

        return {
            "success": False,
            "error": f"OperadicFlow '{operadic_flow_id}' not found"
        }

    except Exception as e:
        logger.error(f"Error expanding OperadicFlow: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _remove_from_opera_schedule(schedule_entry_id: str):
    """
    Remove item from OPERA schedule.

    Args:
        schedule_entry_id: Schedule entry to remove
    """
    try:
        registry_util_func(
            "delete",
            registry_name=OPERA_SCHEDULE_REGISTRY,
            key=schedule_entry_id
        )
        logger.info(f"Removed from OPERA schedule: {schedule_entry_id}")
    except Exception as e:
        logger.error(f"Error removing from OPERA schedule: {e}", exc_info=True)


# ============================================================================
# HOOK 3: PATTERN DETECTION TRIGGER
# ============================================================================

def trigger_pattern_detection_after_completion() -> Dict[str, Any]:
    """
    Post-tool hook: Trigger pattern detection after Canopy item completion.

    This is called automatically when a Canopy item is marked complete.
    Runs OPERA pattern detection on the operadic_ledger.

    Returns:
        Pattern detection result
    """
    try:
        # Run pattern detection
        result = detect_patterns(min_occurrences=2, sequence_length=2)

        if result.get("success"):
            detected = result.get("detected_patterns", 0)
            stored = result.get("stored_patterns", 0)

            logger.info(f"Pattern detection: {detected} patterns detected, {stored} stored to quarantine")

            return {
                "success": True,
                "message": f"Pattern detection complete: {detected} patterns detected, {stored} stored",
                "detected_patterns": detected,
                "stored_patterns": stored
            }
        else:
            logger.warning(f"Pattern detection failed: {result.get('error')}")
            return result

    except Exception as e:
        logger.error(f"Error triggering pattern detection: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
