#!/usr/bin/env python3
"""
CANOPY MCP Server - Master Schedule Orchestration

Provides tools for managing the master schedule of work items with
AI+Human, AI-Only, and Human-Only collaboration types.

Execution tracking happens automatically internally - not exposed as MCP tools.
OPERA MCP reads the operadic_ledger for pattern discovery.
"""

import json
import logging
from fastmcp import FastMCP

# Import schedule functions
from . import schedule

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("CANOPY Master Schedule")


@mcp.tool()
def add_to_schedule(
    item_type: str,
    description: str,
    execution_type: str,
    execution_type_decision_explanation: str,
    priority: int = 5,
    mission_type: str = None,
    mission_type_domain: str = None,
    human_capability: str = None,
    source_type: str = "freestyle",
    source_operadic_flow_id: str = None,
    variables: dict = None,
    metadata: dict = None
) -> str:
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
        human_capability: Optional human capability (for Human-Only or AI+Human tasks - what human focuses on)
        source_type: "freestyle" or "opera" (default: freestyle) - tracks if item added manually or from OperadicFlow
        source_operadic_flow_id: Optional OperadicFlow ID if opera-sourced (for idempotency and meta-pattern detection)
        variables: Optional variables for mission template rendering
        metadata: Optional additional metadata

    Returns:
        Result with item_id and instructions
    """
    result = schedule.add_to_schedule(
        item_type=item_type,
        description=description,
        execution_type=execution_type,
        execution_type_decision_explanation=execution_type_decision_explanation,
        priority=priority,
        mission_type=mission_type,
        mission_type_domain=mission_type_domain,
        human_capability=human_capability,
        source_type=source_type,
        source_operadic_flow_id=source_operadic_flow_id,
        variables=variables,
        metadata=metadata
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def get_next_item(item_type: str = None) -> str:
    """
    Get next pending item from schedule

    Args:
        item_type: Optional filter by type ("AI+Human", "AI-Only", "Human-Only")

    Returns:
        Next item to work on with instructions for activation
    """
    result = schedule.get_next_item(item_type=item_type)
    return json.dumps(result, indent=2)


@mcp.tool()
def view_schedule(status_filter: str = None) -> str:
    """
    View master schedule with optional status filter

    Args:
        status_filter: Optional "pending", "in_progress", "completed"

    Returns:
        Formatted schedule display
    """
    return schedule.view_schedule(status_filter=status_filter)


@mcp.tool()
def mark_complete(item_id: str) -> str:
    """
    Mark schedule item as completed

    Args:
        item_id: Item to mark complete

    Returns:
        Update confirmation
    """
    result = schedule.mark_complete(item_id=item_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def update_item_status(item_id: str, status: str) -> str:
    """
    Update item status

    Args:
        item_id: Item to update
        status: New status ("pending", "in_progress", "completed")

    Returns:
        Update confirmation
    """
    result = schedule.update_item_status(item_id=item_id, status=status)
    return json.dumps(result, indent=2)


def main():
    """Run CANOPY MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()
