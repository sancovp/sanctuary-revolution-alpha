#!/usr/bin/env python3
"""
OPERA MCP Server - Operadic Pattern Discovery and Verification

Provides tools for managing execution patterns discovered from Canopy work:
- View detected patterns (CanopyFlowPatterns in quarantine)
- View verified patterns (OperadicFlows in golden library)
- Promote patterns from quarantine to golden

Pattern detection happens via OMNISANC automation reading operadic_ledger.
Search/goldenization tools will be added after reviewing OMNISANC MCP patterns.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Import HEAVEN registry
try:
    from heaven_base.tools.registry_tool import registry_util_func
except ImportError:
    logger.warning("heaven_base not available - OPERA will not persist", exc_info=True)
    def registry_util_func(*args, **kwargs):
        return "Registry not available"

# Initialize MCP server
mcp = FastMCP("OPERA Pattern Discovery")

# Registry names
CANOPY_PATTERN_REGISTRY = "opera_canopy_patterns"  # Quarantine
OPERADIC_FLOW_REGISTRY = "opera_operadic_flows"    # Golden library
OPERA_SCHEDULE_REGISTRY = "opera_schedule"          # OperadicFlows queued for execution
OPERADIC_LEDGER_REGISTRY = "operadic_ledger"        # Execution history


@mcp.tool()
def view_canopy_patterns(limit: int = 50) -> str:
    """
    View detected CanopyFlowPatterns in quarantine (unverified).

    These are patterns detected by OPERA automation from execution history.
    They require human review before promotion to golden library.

    Args:
        limit: Maximum number of patterns to return (default 50)

    Returns:
        List of detected patterns with metadata
    """
    try:
        patterns = _get_patterns(CANOPY_PATTERN_REGISTRY, limit)

        if not patterns:
            return json.dumps({
                "success": True,
                "count": 0,
                "message": "No CanopyFlowPatterns detected yet. Patterns are auto-detected by OPERA automation.",
                "patterns": []
            }, indent=2)

        return json.dumps({
            "success": True,
            "count": len(patterns),
            "patterns": patterns
        }, indent=2)

    except Exception as e:
        logger.error(f"Error viewing canopy patterns: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def view_quarantine(page: int = 1, per_page: int = 10) -> str:
    """
    Browse CanopyFlowPatterns in quarantine with pagination and numbered selection.

    Mirrors starship.fly() and omnisanc.home() pattern - provides numbered list
    for easy pattern review and selection.

    Args:
        page: Page number (default 1)
        per_page: Items per page (default 10)

    Returns:
        Numbered list of quarantine patterns with pagination
    """
    try:
        # Get all patterns
        patterns = _get_patterns(CANOPY_PATTERN_REGISTRY, limit=1000)

        # Filter to quarantine status only (not promoted/rejected)
        quarantine_patterns = [
            p for p in patterns
            if p.get("status") not in ["promoted", "rejected"]
        ]

        if not quarantine_patterns:
            return """📦 OPERA Quarantine - No Patterns Pending Review

✅ Quarantine is empty! Patterns will appear here after:
- Completing Canopy work items
- OPERA automation detecting patterns in operadic_ledger
- Patterns waiting for human review

Use opera.view_operadic_flows() to see golden patterns."""

        # Pagination
        total_patterns = len(quarantine_patterns)
        total_pages = (total_patterns + per_page - 1) // per_page

        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_patterns = quarantine_patterns[start_idx:end_idx]

        # Build numbered list
        lines = [f"📦 OPERA Quarantine - Pattern Review (Page {page}/{total_pages})"]
        lines.append("=" * 60)
        lines.append(f"Total Patterns: {total_patterns}\n")

        for idx, pattern in enumerate(page_patterns, start=start_idx + 1):
            pattern_id = pattern.get("pattern_id", "unknown")
            name = pattern.get("name", "Unnamed Pattern")
            detected_at = pattern.get("detected_at", "unknown")
            occurrences = pattern.get("occurrences", 0)
            sequence_length = len(pattern.get("sequence", []))

            lines.append(f"{idx}. {name}")
            lines.append(f"   ID: {pattern_id}")
            lines.append(f"   Detected: {detected_at}")
            lines.append(f"   Occurrences: {occurrences} | Steps: {sequence_length}")
            lines.append("")

        lines.append("-" * 60)
        lines.append("\n📋 Actions:")
        lines.append("   - opera.get_pattern_details(pattern_id) - View full pattern")
        lines.append("   - opera.goldenize_flow_to_operadic(pattern_id, verified_by, notes) - Accept")
        lines.append("   - opera.reject_pattern(pattern_id, reason) - Reject")

        if page < total_pages:
            lines.append(f"\n➡️  Next page: opera.view_quarantine(page={page + 1})")
        if page > 1:
            lines.append(f"⬅️  Previous page: opera.view_quarantine(page={page - 1})")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error viewing quarantine: {e}", exc_info=True)
        return f"❌ Error viewing quarantine: {str(e)}"


@mcp.tool()
def view_operadic_flows(limit: int = 50) -> str:
    """
    View verified OperadicFlows in golden library (production-ready).

    These are patterns that have been reviewed and promoted from quarantine.
    They can be reused for spawning TreeKanban cards.

    Args:
        limit: Maximum number of flows to return (default 50)

    Returns:
        List of golden verified patterns
    """
    try:
        flows = _get_patterns(OPERADIC_FLOW_REGISTRY, limit)

        if not flows:
            return json.dumps({
                "success": True,
                "count": 0,
                "message": "No OperadicFlows in golden library yet. Promote patterns with promote_pattern().",
                "flows": []
            }, indent=2)

        return json.dumps({
            "success": True,
            "count": len(flows),
            "flows": flows
        }, indent=2)

    except Exception as e:
        logger.error(f"Error viewing operadic flows: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def get_pattern_details(pattern_id: str, pattern_type: str = "canopy") -> str:
    """
    Get detailed information about a specific pattern.

    Args:
        pattern_id: Pattern identifier
        pattern_type: "canopy" for CanopyFlowPattern or "operadic" for OperadicFlow

    Returns:
        Complete pattern data with detection metadata
    """
    try:
        registry_name = CANOPY_PATTERN_REGISTRY if pattern_type == "canopy" else OPERADIC_FLOW_REGISTRY

        result = registry_util_func(
            "get",
            registry_name=registry_name,
            key=pattern_id
        )

        # Parse registry result
        pattern = _parse_registry_get_result(result)

        if not pattern:
            return json.dumps({
                "success": False,
                "error": f"Pattern '{pattern_id}' not found in {pattern_type} registry"
            }, indent=2)

        return json.dumps({
            "success": True,
            "pattern": pattern
        }, indent=2)

    except Exception as e:
        logger.error(f"Error getting pattern details: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def promote_pattern(
    pattern_id: str,
    verified_by: str,
    notes: str = None
) -> str:
    """
    Promote CanopyFlowPattern to OperadicFlow (quarantine → golden library).

    This marks a pattern as reviewed and production-ready for reuse.

    Args:
        pattern_id: CanopyFlowPattern ID to promote
        verified_by: Who verified this pattern (username/identifier)
        notes: Optional verification notes

    Returns:
        Promotion result with new OperadicFlow ID
    """
    try:
        # Get pattern from quarantine
        result = registry_util_func(
            "get",
            registry_name=CANOPY_PATTERN_REGISTRY,
            key=pattern_id
        )

        pattern = _parse_registry_get_result(result)

        if not pattern:
            return json.dumps({
                "success": False,
                "error": f"CanopyFlowPattern '{pattern_id}' not found in quarantine"
            }, indent=2)

        # Create OperadicFlow from CanopyFlowPattern
        operadic_flow_id = f"operadic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        operadic_flow = {
            **pattern,  # Copy all pattern data
            "operadic_flow_id": operadic_flow_id,
            "original_pattern_id": pattern_id,
            "promoted_at": datetime.now().isoformat(),
            "verified_by": verified_by,
            "verification_notes": notes,
            "status": "golden"
        }

        # Write to golden library
        registry_util_func(
            "add",
            registry_name=OPERADIC_FLOW_REGISTRY,
            key=operadic_flow_id,
            value_dict=operadic_flow
        )

        # Update quarantine pattern status
        pattern["promoted_to"] = operadic_flow_id
        pattern["promoted_at"] = datetime.now().isoformat()
        pattern["status"] = "promoted"

        registry_util_func(
            "update",
            registry_name=CANOPY_PATTERN_REGISTRY,
            key=pattern_id,
            value_dict=pattern
        )

        # Update quarantine count registry
        _update_quarantine_count_registry()

        logger.info(f"Promoted pattern {pattern_id} → {operadic_flow_id}")

        return json.dumps({
            "success": True,
            "operadic_flow_id": operadic_flow_id,
            "message": f"Promoted CanopyFlowPattern to golden library",
            "original_pattern_id": pattern_id
        }, indent=2)

    except Exception as e:
        logger.error(f"Error promoting pattern: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def goldenize_flow_to_operadic(
    pattern_id: str,
    verified_by: str,
    notes: str = None
) -> str:
    """
    Goldenize CanopyFlowPattern to OperadicFlow (accept pattern from quarantine).

    Alias for promote_pattern() with clearer naming that matches OPERA terminology.
    Accepts a pattern from quarantine and promotes it to the golden library.

    Args:
        pattern_id: CanopyFlowPattern ID to goldenize
        verified_by: Who verified this pattern (username/identifier)
        notes: Optional verification notes

    Returns:
        Goldenization result with new OperadicFlow ID
    """
    return promote_pattern(pattern_id, verified_by, notes)


@mcp.tool()
def reject_pattern(pattern_id: str, reason: str = None) -> str:
    """
    Reject CanopyFlowPattern from quarantine.

    Marks pattern as rejected (soft delete) rather than promoting to golden library.
    Rejected patterns remain in registry for analysis but won't appear in quarantine reviews.

    Args:
        pattern_id: CanopyFlowPattern ID to reject
        reason: Optional rejection reason

    Returns:
        Rejection confirmation
    """
    try:
        # Get pattern from quarantine
        result = registry_util_func(
            "get",
            registry_name=CANOPY_PATTERN_REGISTRY,
            key=pattern_id
        )

        pattern = _parse_registry_get_result(result)

        if not pattern:
            return json.dumps({
                "success": False,
                "error": f"CanopyFlowPattern '{pattern_id}' not found in quarantine"
            }, indent=2)

        # Check if already processed
        current_status = pattern.get("status")
        if current_status == "promoted":
            return json.dumps({
                "success": False,
                "error": f"Pattern '{pattern_id}' already promoted to golden library"
            }, indent=2)

        if current_status == "rejected":
            return json.dumps({
                "success": False,
                "error": f"Pattern '{pattern_id}' already rejected"
            }, indent=2)

        # Update pattern status to rejected
        pattern["status"] = "rejected"
        pattern["rejected_at"] = datetime.now().isoformat()
        pattern["rejection_reason"] = reason

        registry_util_func(
            "update",
            registry_name=CANOPY_PATTERN_REGISTRY,
            key=pattern_id,
            value_dict=pattern
        )

        # Update quarantine count registry
        _update_quarantine_count_registry()

        logger.info(f"Rejected pattern {pattern_id}: {reason}")

        return json.dumps({
            "success": True,
            "pattern_id": pattern_id,
            "message": f"Rejected CanopyFlowPattern from quarantine",
            "rejection_reason": reason
        }, indent=2)

    except Exception as e:
        logger.error(f"Error rejecting pattern: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


def _get_patterns(registry_name: str, limit: int) -> List[Dict[str, Any]]:
    """
    Get patterns from registry.

    Args:
        registry_name: Registry to query
        limit: Maximum number of patterns

    Returns:
        List of pattern dictionaries
    """
    try:
        result = registry_util_func("get_all", registry_name=registry_name)

        # Parse registry result
        if "Items in registry" in result:
            try:
                start_idx = result.find("{")
                if start_idx != -1:
                    dict_str = result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    patterns_dict = json.loads(dict_str.replace("'", '"'))
                    patterns = list(patterns_dict.values())[:limit]
                    return patterns
            except Exception:
                logger.warning(f"Failed to parse registry result", exc_info=True)

        return []

    except Exception as e:
        logger.error(f"Failed to get patterns from {registry_name}: {e}", exc_info=True)
        return []


def _parse_registry_get_result(result: str) -> Optional[Dict[str, Any]]:
    """
    Parse registry get result into dictionary.

    Args:
        result: Registry get result string

    Returns:
        Parsed dictionary or None
    """
    try:
        # heaven-framework registry_util_func returns: "Item '{key}' in registry '{registry_name}': {item}"
        if "Item '" in result and "' in registry '" in result:
            start_idx = result.find("{")
            if start_idx != -1:
                dict_str = result[start_idx:]
                dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                return json.loads(dict_str.replace("'", '"'))
        return None
    except Exception:
        logger.warning("Failed to parse registry get result", exc_info=True)
        return None


# ============================================================================
# OPERA SCHEDULE MANAGEMENT (OperadicFlow execution queue)
# ============================================================================

@mcp.tool()
def add_to_opera_schedule(
    title: str,
    body: str,
    starlog_projects: list,
    operadic_flow_id: str = None,
    priority: int = 5
) -> str:
    """
    Add OperadicFlow instance to OPERA schedule for execution.

    OperadicFlow is the template (capability sequence), this creates an
    instance with specific work context (title, body, projects).

    OPERA schedule feeds Canopy schedule via OMNISANC hook.
    When Canopy schedule is empty, top 3 OPERA items expand into Canopy.

    Args:
        title: Instance-specific title (e.g., "Implement OAuth for user service")
        body: Instance-specific description/details
        starlog_projects: List of STARLOG project paths this work applies to
        operadic_flow_id: OperadicFlow ID from golden library (defaults to "default_human_ai_collaboration")
        priority: 1-10 priority (10 = highest, default 5)

    Returns:
        Schedule addition confirmation
    """
    try:
        # Default to default_human_ai_collaboration if no flow specified
        if operadic_flow_id is None:
            operadic_flow_id = "default_human_ai_collaboration"

        # Get OperadicFlow from golden library
        result = registry_util_func(
            "get",
            registry_name=OPERADIC_FLOW_REGISTRY,
            key=operadic_flow_id
        )

        operadic_flow = _parse_registry_get_result(result)

        if not operadic_flow:
            return json.dumps({
                "success": False,
                "error": f"OperadicFlow '{operadic_flow_id}' not found in golden library"
            }, indent=2)

        # Create schedule entry (instance of OperadicFlow)
        schedule_entry_id = f"opera_sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        schedule_entry = {
            "schedule_entry_id": schedule_entry_id,
            "operadic_flow_id": operadic_flow_id,
            "operadic_flow": operadic_flow,
            "title": title,
            "body": body,
            "starlog_projects": starlog_projects,
            "priority": priority,
            "status": "queued",
            "queued_at": datetime.now().isoformat()
        }

        # Add to OPERA schedule
        registry_util_func(
            "add",
            registry_name=OPERA_SCHEDULE_REGISTRY,
            key=schedule_entry_id,
            value_dict=schedule_entry
        )

        logger.info(f"Added OperadicFlow instance to OPERA schedule: {title}")

        return json.dumps({
            "success": True,
            "schedule_entry_id": schedule_entry_id,
            "message": f"OperadicFlow instance '{title}' queued for execution",
            "priority": priority
        }, indent=2)

    except Exception as e:
        logger.error(f"Error adding to OPERA schedule: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def view_opera_schedule() -> str:
    """
    View OPERA schedule (OperadicFlows queued for execution).

    Shows which patterns are scheduled to feed into Canopy.

    Returns:
        List of scheduled OperadicFlows sorted by priority
    """
    try:
        schedule_items = _get_patterns(OPERA_SCHEDULE_REGISTRY, limit=100)

        if not schedule_items:
            return json.dumps({
                "success": True,
                "count": 0,
                "message": "OPERA schedule is empty. Canopy freestyle is unlocked.",
                "schedule": []
            }, indent=2)

        # Sort by priority (highest first), then by queued_at
        schedule_items.sort(key=lambda x: (-x.get("priority", 5), x.get("queued_at", "")))

        return json.dumps({
            "success": True,
            "count": len(schedule_items),
            "message": f"OPERA schedule has {len(schedule_items)} items. Canopy freestyle is LOCKED.",
            "schedule": schedule_items
        }, indent=2)

    except Exception as e:
        logger.error(f"Error viewing OPERA schedule: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def get_top_opera_items(count: int = 3) -> str:
    """
    Get top N OperadicFlows from OPERA schedule for Canopy feeding.

    Used by OMNISANC hook to feed Canopy schedule when empty.

    Args:
        count: Number of items to retrieve (default 3)

    Returns:
        Top N OperadicFlows by priority
    """
    try:
        schedule_items = _get_patterns(OPERA_SCHEDULE_REGISTRY, limit=100)

        if not schedule_items:
            return json.dumps({
                "success": True,
                "count": 0,
                "items": []
            }, indent=2)

        # Sort by priority (highest first), then by queued_at
        schedule_items.sort(key=lambda x: (-x.get("priority", 5), x.get("queued_at", "")))

        # Take top N
        top_items = schedule_items[:count]

        return json.dumps({
            "success": True,
            "count": len(top_items),
            "items": top_items
        }, indent=2)

    except Exception as e:
        logger.error(f"Error getting top OPERA items: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def remove_from_opera_schedule(schedule_entry_id: str) -> str:
    """
    Remove item from OPERA schedule.

    Used after OperadicFlow has been expanded into Canopy.

    Args:
        schedule_entry_id: Schedule entry to remove

    Returns:
        Removal confirmation
    """
    try:
        registry_util_func(
            "delete",
            registry_name=OPERA_SCHEDULE_REGISTRY,
            key=schedule_entry_id
        )

        logger.info(f"Removed from OPERA schedule: {schedule_entry_id}")

        return json.dumps({
            "success": True,
            "message": f"Removed {schedule_entry_id} from OPERA schedule"
        }, indent=2)

    except Exception as e:
        logger.error(f"Error removing from OPERA schedule: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def expand_operadic_flow_to_canopy_items(operadic_flow_id: str) -> str:
    """
    Expand OperadicFlow into Canopy schedule items.

    Takes an OperadicFlow from golden library and generates the Canopy
    items needed to execute it. Returns the items as data for Canopy to add.

    Used by OMNISANC hook to feed OPERA schedule into Canopy.

    Args:
        operadic_flow_id: OperadicFlow to expand

    Returns:
        List of Canopy item dicts ready for adding to schedule
    """
    try:
        # Get OperadicFlow from golden library
        result = registry_util_func(
            "get",
            registry_name=OPERADIC_FLOW_REGISTRY,
            key=operadic_flow_id
        )

        operadic_flow = _parse_registry_get_result(result)

        if not operadic_flow:
            return json.dumps({
                "success": False,
                "error": f"OperadicFlow '{operadic_flow_id}' not found in golden library"
            }, indent=2)

        # OperadicFlow should have 'sequence' array of steps
        # Each step has: item_type, mission_type, human_capability, execution_type, etc.
        sequence = operadic_flow.get("sequence", [])

        if not sequence:
            return json.dumps({
                "success": False,
                "error": f"OperadicFlow '{operadic_flow_id}' has no sequence defined"
            }, indent=2)

        # Generate Canopy items from sequence
        canopy_items = []
        for idx, step in enumerate(sequence):
            canopy_item = {
                "item_type": step.get("item_type"),
                "description": step.get("description", f"Step {idx + 1} of {operadic_flow.get('name', operadic_flow_id)}"),
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

        return json.dumps({
            "success": True,
            "operadic_flow_id": operadic_flow_id,
            "canopy_items": canopy_items,
            "count": len(canopy_items)
        }, indent=2)

    except Exception as e:
        logger.error(f"Error expanding OperadicFlow: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


def auto_populate_default_operadic_flow() -> str:
    """
    Auto-populate default OperadicFlow for bootstrapping OPERA schedule.

    Creates a basic Human+AI collaboration flow that can be used when
    no patterns have been detected yet. This allows OPERA schedule to
    work before pattern detection has created golden flows.

    Returns:
        Status message
    """
    try:
        # Check if default already exists
        result = registry_util_func(
            "get",
            registry_name=OPERADIC_FLOW_REGISTRY,
            key="default_human_ai_collaboration"
        )

        if "Value for key" in result:
            logger.info("Default OperadicFlow already exists - skipping auto-population")
            return "✅ Default OperadicFlow already exists"

        # Create default OperadicFlow
        default_flow = {
            "operadic_flow_id": "default_human_ai_collaboration",
            "name": "Default Human+AI Collaboration",
            "description": "Default collaborative work pattern for bootstrapping OPERA before pattern detection",
            "sequence": [{
                "item_type": "AI+Human",
                "execution_type": "plotted_course",
                "execution_type_decision_explanation": "Default collaborative work - AI and human work together using plotted course workflow",
                "priority": 5,
                "mission_type": None,
                "mission_type_domain": None,
                "human_capability": "general",
                "description": "Collaborative AI+Human work item",
                "variables": {},
                "metadata": {}
            }],
            "status": "golden",
            "is_default": True,
            "promoted_at": datetime.now().isoformat(),
            "verified_by": "system",
            "verification_notes": "Auto-populated default flow for OPERA bootstrapping"
        }

        # Add to golden library
        registry_util_func(
            "add",
            registry_name=OPERADIC_FLOW_REGISTRY,
            key="default_human_ai_collaboration",
            value_dict=default_flow
        )

        # Initialize quarantine count registry
        _update_quarantine_count_registry()

        logger.info("Auto-populated default OperadicFlow: default_human_ai_collaboration")
        return "✅ Created default OperadicFlow: default_human_ai_collaboration"

    except Exception as e:
        logger.error(f"Failed to auto-populate default OperadicFlow: {e}", exc_info=True)
        return f"❌ Failed to auto-populate default: {str(e)}"


def _update_quarantine_count_registry():
    """
    Update quarantine count in registry for external systems to read.

    OPERA maintains this count, SEED reads it (no direct dependency).
    Called after any pattern status change.
    """
    try:
        patterns = _get_patterns(CANOPY_PATTERN_REGISTRY, limit=1000)
        quarantine_patterns = [
            p for p in patterns
            if p.get("status") not in ["promoted", "rejected"]
        ]
        count = len(quarantine_patterns)

        # Write to registry
        registry_util_func(
            "add",
            registry_name="opera_metrics",
            key="quarantine_count",
            value_dict={"count": count, "updated_at": datetime.now().isoformat()}
        )

        logger.debug(f"Updated quarantine count registry: {count}")
        return count
    except Exception as e:
        logger.error(f"Error updating quarantine count registry: {e}", exc_info=True)
        return 0


@mcp.tool()
def vendor_operadic_flow(
    project_id: str,
    feature_name: str,
    component_name: str,
    deliverable_name: str,
    operadic_flow_id: str
) -> str:
    """
    Vendor OperadicFlow to GIINT deliverable.

    Adds OperadicFlow ID to deliverable's operadic_flow_ids list.
    When synced to TreeKanban, the OperadicFlow step cards will be created
    as children of the deliverable card.

    Args:
        project_id: GIINT project ID
        feature_name: Feature containing the deliverable
        component_name: Component containing the deliverable
        deliverable_name: Deliverable to vendor OperadicFlow to
        operadic_flow_id: OperadicFlow ID from golden library

    Returns:
        Vendoring result with updated deliverable info
    """
    try:
        # Import GIINT project registry
        from llm_intelligence.projects import ProjectRegistry

        # Validate OperadicFlow exists in golden library
        result = registry_util_func(
            "get",
            registry_name=OPERADIC_FLOW_REGISTRY,
            key=operadic_flow_id
        )

        operadic_flow = _parse_registry_get_result(result)
        if not operadic_flow:
            return json.dumps({
                "success": False,
                "error": f"OperadicFlow '{operadic_flow_id}' not found in golden library"
            }, indent=2)

        # Load GIINT project
        registry = ProjectRegistry()
        projects = registry._load_projects()

        if project_id not in projects:
            return json.dumps({
                "success": False,
                "error": f"GIINT project '{project_id}' not found"
            }, indent=2)

        project = projects[project_id]

        # Navigate to deliverable
        if feature_name not in project.features:
            return json.dumps({
                "success": False,
                "error": f"Feature '{feature_name}' not found in project '{project_id}'"
            }, indent=2)

        feature = project.features[feature_name]

        if component_name not in feature.components:
            return json.dumps({
                "success": False,
                "error": f"Component '{component_name}' not found in feature '{feature_name}'"
            }, indent=2)

        component = feature.components[component_name]

        if deliverable_name not in component.deliverables:
            return json.dumps({
                "success": False,
                "error": f"Deliverable '{deliverable_name}' not found in component '{component_name}'"
            }, indent=2)

        deliverable = component.deliverables[deliverable_name]

        # Check if already vendored
        if operadic_flow_id in deliverable.operadic_flow_ids:
            return json.dumps({
                "success": False,
                "error": f"OperadicFlow '{operadic_flow_id}' already vendored to deliverable '{deliverable_name}'"
            }, indent=2)

        # Add OperadicFlow ID to deliverable
        deliverable.operadic_flow_ids.append(operadic_flow_id)

        # Save project
        registry._save_projects(projects)

        logger.info(f"Vendored OperadicFlow {operadic_flow_id} to {project_id}/{feature_name}/{component_name}/{deliverable_name}")

        return json.dumps({
            "success": True,
            "message": f"Vendored OperadicFlow '{operadic_flow.get('name', operadic_flow_id)}' to deliverable '{deliverable_name}'",
            "project_id": project_id,
            "deliverable_path": f"{feature_name}/{component_name}/{deliverable_name}",
            "operadic_flow_id": operadic_flow_id,
            "operadic_flow_name": operadic_flow.get("name", "Unknown"),
            "total_vendored_flows": len(deliverable.operadic_flow_ids)
        }, indent=2)

    except Exception as e:
        logger.error(f"Error vendoring OperadicFlow: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


def _check_and_auto_populate():
    """Check if default OperadicFlow exists and auto-populate if needed."""
    try:
        result = auto_populate_default_operadic_flow()
        logger.info(f"Auto-population check: {result}")
    except Exception as e:
        logger.error(f"Failed auto-population check: {e}", exc_info=True)


def main():
    """Run OPERA MCP server"""
    # Auto-populate default OperadicFlow on startup if needed
    _check_and_auto_populate()

    # Start MCP server
    mcp.run()


if __name__ == "__main__":
    main()
