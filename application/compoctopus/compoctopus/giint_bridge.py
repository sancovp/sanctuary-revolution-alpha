"""GIINT Bridge — re-exports from llm_intelligence.projects.

This module exists solely to provide Compoctopus-local imports of the
GIINT project hierarchy types. All types come from the real
llm_intelligence package — no mirrors, no duplicates.

The Planner agent uses the giint-llm-intelligence MCP tools directly
to create/query the hierarchy. This module is for Python-side type
access only (e.g., reading a Project after the Planner builds it).
"""

from __future__ import annotations

# Re-export the real GIINT types from llm_intelligence.projects
from llm_intelligence.projects import (
    # Enums
    TaskStatus,
    AssigneeType,
    ProjectType,
    # Hierarchy models
    Task,
    Deliverable,
    Component,
    Feature,
    Project,
    # Spec models
    FeatureSpec,
    ComponentSpec,
    DeliverableSpec,
    TaskSpec as GIINTTaskSpec,
    # Registry
    ProjectRegistry,
    get_registry,
    # Top-level functions (same as MCP tools call internally)
    create_project,
    get_project,
    list_projects,
    delete_project,
    add_feature_to_project,
    add_component_to_feature,
    add_deliverable_to_component,
    add_task_to_deliverable,
    update_task_status,
    update_project_mode,
    add_spec_to_feature,
    add_spec_to_component,
    add_spec_to_deliverable,
    add_spec_to_task,
)

__all__ = [
    "TaskStatus",
    "AssigneeType",
    "ProjectType",
    "Task",
    "Deliverable",
    "Component",
    "Feature",
    "Project",
    "FeatureSpec",
    "ComponentSpec",
    "DeliverableSpec",
    "GIINTTaskSpec",
    "ProjectRegistry",
    "get_registry",
    "create_project",
    "get_project",
    "list_projects",
    "delete_project",
    "add_feature_to_project",
    "add_component_to_feature",
    "add_deliverable_to_component",
    "add_task_to_deliverable",
    "update_task_status",
    "update_project_mode",
    "add_spec_to_feature",
    "add_spec_to_component",
    "add_spec_to_deliverable",
    "add_spec_to_task",
    "ProjectCompiler",
]


# =============================================================================
# ProjectCompiler — Link whose execute() runs the Planner agent
# =============================================================================

from compoctopus.chain_ontology import Link, LinkResult, LinkStatus


class ProjectCompiler(Link):
    """Link that decomposes a goal into a GIINT project hierarchy.

    execute() creates and runs the Planner agent, which uses the
    giint-llm-intelligence MCP to build the Project → Feature →
    Component → Deliverable → Task hierarchy.

    Context in:
        _goal (str): high-level goal to decompose

    Context out:
        _project_id (str): ID of the created project
    """

    def __init__(self, planner_factory=None):
        """
        Args:
            planner_factory: callable that returns a CompoctopusAgent
                             (Planner). Defaults to make_planner().
        """
        self.planner_factory = planner_factory
        self.name = "project_compiler"

    async def execute(self, context=None, **kwargs):
        ctx = dict(context) if context else {}
        goal = ctx.get("_goal", "")
        if not goal:
            return LinkResult(
                status=LinkStatus.ERROR,
                context=ctx,
                error="No _goal in context",
            )

        # Lazy import to avoid circular deps
        if self.planner_factory:
            planner = self.planner_factory()
        else:
            from compoctopus.octopus_coder import make_planner
            planner = make_planner()

        result = await planner.execute(ctx)
        return result

    def describe(self, depth=0):
        indent = "  " * depth
        return f'{indent}ProjectCompiler "{self.name}" → Planner agent'
