"""Integration test: Run the Planner agent against a real goal.

This test creates a Planner via make_planner() and runs it with
a goal + project_id. The Planner uses the giint-llm-intelligence
MCP to create the GIINT hierarchy:

    Project → Feature → Component → Deliverable → Task

Usage:
    python3 -m compoctopus.integration.run_planner

Requires:
    - HEAVEN_DATA_DIR set (for Heaven + GIINT MCP)
    - system_config.sh sourced (API keys)
    - giint-llm-intelligence package installed
"""

import asyncio
import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
logger = logging.getLogger("run_planner")


async def run_planner_integration(
    request: str,
    project_id: str = None,
):
    """Run the Planner agent with a real goal.

    Args:
        request: what to decompose
        project_id: existing project or None (Planner creates one)
    """
    from compoctopus.octopus_coder import make_planner

    logger.info("=" * 60)
    logger.info("PLANNER INTEGRATION TEST")
    logger.info("=" * 60)
    logger.info(f"Request: {request}")
    logger.info(f"Project ID: {project_id or '(new project)'}")
    logger.info("")

    # Build context
    ctx = {
        "request": request,
        "project_id": project_id,
    }

    # Create and run the Planner
    planner = make_planner()
    logger.info(f"Planner created: {planner.agent_name}")
    logger.info(f"Initial state: {planner.state_machine.current_state}")
    logger.info(f"SM states: {list(planner.state_machine.states.keys())}")
    logger.info(f"MCP servers: {list(planner.hermes_config.mcp_servers.keys())}")
    logger.info("")

    logger.info("Starting Planner execution...")
    logger.info("-" * 60)

    result = await planner.execute(ctx)

    logger.info("-" * 60)
    logger.info("Planner execution complete")
    logger.info(f"Final state: {planner.state_machine.current_state}")
    logger.info(f"Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
    logger.info("")

    # Check what GIINT hierarchy was created
    try:
        from llm_intelligence.projects import get_registry
        registry = get_registry()
        projects = registry.list_projects()
        logger.info(f"GIINT projects after run: {json.dumps(projects, indent=2, default=str)[:500]}")
    except Exception as e:
        logger.warning(f"Could not query GIINT registry: {e}")

    return result


# ── Test Goals ────────────────────────────────────────────────────

SIMPLE_GOAL = (
    "Build a CLI tool called 'octosearch' that searches .octo files "
    "in a directory and reports which ones have failing tests. "
    "It should support --dir and --verbose flags."
)

EXISTING_PROJECT_GOAL = (
    "Add a new compiler arm to Compoctopus that handles MCP server "
    "configuration. It should validate that all tool references in "
    "the system prompt match the MCP tool surface."
)


if __name__ == "__main__":
    goal = sys.argv[1] if len(sys.argv) > 1 else SIMPLE_GOAL
    project_id = sys.argv[2] if len(sys.argv) > 2 else None

    result = asyncio.run(run_planner_integration(goal, project_id))

    print("\n" + "=" * 60)
    print("RESULT:")
    print(json.dumps(result, indent=2, default=str)[:1000] if isinstance(result, dict) else result)
