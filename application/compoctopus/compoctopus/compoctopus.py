"""Compoctopus — the top-level self-compiling agent compiler.

Flow:
    PRD → Planner → Bandit → Workers (OctoCoder default)

The Planner decomposes the PRD into a GIINT hierarchy.
The Bandit routes each task to the right worker.
The OctoCoder builds code for tasks routed to it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, FunctionLink, LinkResult, LinkStatus
from compoctopus.types import SystemPrompt, PromptSection
from compoctopus.prd import PRD

logger = logging.getLogger(__name__)


def make_compoctopus(
    prd: PRD,
    workspace: str = "/tmp/compoctopus_output",
    workers: Optional[Dict[str, CompoctopusAgent]] = None,
) -> CompoctopusAgent:
    """Create the top-level Compoctopus agent.

    Args:
        prd: The typed PRD — one for the entire pipeline.
        workspace: Where to write output files.
        workers: Optional dict of worker agents by name.
                 Default: {"octopus_coder": make_octopus_coder(...)}.

    Returns:
        CompoctopusAgent with chain: Planner → Dispatch → (Bandit per task)
    """
    from compoctopus.agents.planner.factory import make_planner
    from compoctopus.agents.octopus_coder.factory import make_octopus_coder

    # --- 1. Planner ---
    planner = make_planner(workspace=workspace)

    # --- 2. Default workers ---
    if workers is None:
        workers = {
            "octopus_coder": make_octopus_coder(
                spec=prd.to_spec_string(),
                workspace=workspace,
            ),
        }

    # --- 3. Dispatch link ---
    # After the Planner creates the GIINT hierarchy, this link
    # queries the tasks and dispatches each to the Bandit → Worker.
    async def dispatch_tasks(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Read GIINT tasks, dispatch each through Bandit → Worker."""
        project_id = ctx.get("project_id")
        task_results = []

        if project_id:
            # Try to get tasks from llm-intelligence
            try:
                from llm_intelligence.projects import get_project
                project = get_project(project_id)
                tasks = _extract_tasks(project)
                logger.info("Dispatching %d tasks from GIINT project %s",
                           len(tasks), project_id)
            except (ImportError, Exception) as e:
                logger.warning("Could not read GIINT project: %s. "
                             "Falling back to PRD spec.", e)
                tasks = [{"description": prd.description, "spec": prd.to_spec_string()}]
        else:
            # No project_id — planner didn't create one or we're in test mode
            logger.info("No project_id in context, using PRD directly")
            tasks = [{"description": prd.description, "spec": prd.to_spec_string()}]

        # Dispatch each task to the default worker (octopus_coder)
        # In full Compoctopus, the Bandit routes each task
        default_worker = workers.get("octopus_coder")
        for i, task in enumerate(tasks):
            logger.info("Task %d/%d: %s", i + 1, len(tasks),
                       task.get("description", "")[:80])
            if default_worker:
                try:
                    result = await default_worker.execute({
                        "task": task.get("description", ""),
                        "spec": task.get("spec", prd.to_spec_string()),
                        "workspace": workspace,
                    })
                    task_results.append({
                        "task": task,
                        "status": str(result.status),
                        "error": result.error,
                    })
                except Exception as e:
                    logger.error("Task %d failed: %s", i + 1, e)
                    task_results.append({
                        "task": task,
                        "status": "error",
                        "error": str(e),
                    })

        ctx["task_results"] = task_results
        ctx["completed"] = len([r for r in task_results if "error" not in r or r["error"] is None])
        ctx["total_tasks"] = len(tasks)
        return ctx

    dispatch_link = FunctionLink(
        link_name="dispatch",
        fn=dispatch_tasks,
    )

    # --- 4. Compose ---
    chain = Chain(
        chain_name="compoctopus",
        links=[planner, dispatch_link],
    )

    return CompoctopusAgent(
        agent_name="compoctopus",
        chain=chain,
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are Compoctopus — the self-compiling agent compiler.\n"
                    "You take a typed PRD and produce working code through:\n"
                    "  1. Planner: decompose PRD into GIINT hierarchy\n"
                    "  2. Bandit: route each task to the right worker\n"
                    "  3. Workers: build code (OctoCoder is the default)\n"
                ),
            ),
        ]),
        model="minimax",
    )


def _extract_tasks(project: dict) -> List[dict]:
    """Extract all tasks from a GIINT project hierarchy."""
    tasks = []
    for feature in project.get("features", []):
        for component in feature.get("components", []):
            for deliverable in component.get("deliverables", []):
                for task in deliverable.get("tasks", []):
                    tasks.append({
                        "description": task.get("description", task.get("name", "")),
                        "feature": feature.get("name", ""),
                        "component": component.get("name", ""),
                        "deliverable": deliverable.get("name", ""),
                        "spec": task.get("spec", ""),
                    })
    return tasks if tasks else [{"description": project.get("description", ""), "spec": ""}]
